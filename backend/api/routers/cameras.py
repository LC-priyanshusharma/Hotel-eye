from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import shutil
import os
import json
import time
import asyncio

from database.session import SessionLocal
from database.models.models import Camera
from database.repositories.camera_repository import CameraRepository
from config.config import redis_client, config
from app.auth.dependencies import get_current_user
# Still import camera_manager for legacy local pipelines if needed, but we prefer Redis now.
from core.camera_manager import camera_manager
from core.ffmpeg_manager import ffmpeg_manager

router = APIRouter(prefix="/api/cameras", tags=["Cameras"], dependencies=[Depends(get_current_user)])

class CameraInfo(BaseModel):
    name: str
    rtsp_url: str = None
    source_type: str = "rtsp"
    source: str = None
    edge_id: str = "edge-01"

class CameraControl(BaseModel):
    camera_id: str

def publish_redis_command(command: str, camera_id: str, edge_id: str, url: str = None):
    # Map command format to what DeepStreamMessageBroker expects
    action_map = {
        "start_camera": "start",
        "stop_camera": "stop"
    }
    payload = {
        "action": action_map.get(command, command),
        "camera_id": camera_id,
        "edge_id": edge_id
    }
    if url:
        payload["url"] = url
    redis_client.publish("camera_commands", json.dumps(payload))

# NOTE: Do NOT URL-encode RTSP credentials here.
# GStreamer's rtspsrc handles special characters (like @ in passwords) internally.
# Encoding them causes double-encoding and authentication failures.


@router.post("")
def post_camera(camera: CameraInfo, background_tasks: BackgroundTasks):
    import uuid
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cam_id = str(uuid.uuid4())
        
        actual_source = camera.source if camera.source else camera.rtsp_url
        
        existing = repo.get_by_name(camera.name)
        if existing:
            cam_id = existing.id
            existing.rtsp_url = actual_source
            existing.source_type = camera.source_type
            existing.source = actual_source
            existing.edge_id = camera.edge_id
            db.commit()
        else:
            new_cam = Camera(
                id=cam_id,
                name=camera.name,
                rtsp_url=actual_source,
                source_type=camera.source_type,
                source=actual_source,
                active=True,
                state="STOPPED",
                edge_id=camera.edge_id
            )
            repo.add(new_cam)
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()
    cam_dict = camera.model_dump()
    cam_dict["id"] = cam_id
    return {"status": "success", "camera_id": cam_id, "camera": cam_dict}

@router.put("/{cam_id}")
def update_camera(cam_id: str, camera: CameraInfo, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        existing = repo.get_by_id(cam_id)
        if not existing:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Camera not found"})
        
        actual_source = camera.source if camera.source else camera.rtsp_url
        
        existing.name = camera.name
        existing.rtsp_url = actual_source
        existing.source_type = camera.source_type
        existing.source = actual_source
        existing.edge_id = camera.edge_id
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()
        
    return {"status": "success", "message": "Camera updated"}

@router.post("/start")
def start_camera(control: CameraControl, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        target_cam = repo.get_by_id(control.camera_id)
        if target_cam:
            # Idempotency Check
            if target_cam.state in ["Connecting/Offline", "Connected", "RUNNING"]:
                return {"status": "success", "message": "Camera is already starting or running."}
                
            target_cam.state = "Connecting/Offline"
            db.commit()
            
            source = getattr(target_cam, 'source', target_cam.rtsp_url)
            source_type = getattr(target_cam, 'source_type', 'rtsp')
            edge_id = getattr(target_cam, 'edge_id', 'edge-01')
            
            if source:
                source = ffmpeg_manager.start_stream(target_cam.id, source)
                
            publish_redis_command("start_camera", target_cam.id, edge_id, source)
            
            return {"status": "success", "message": "Camera start initiated on edge."}
        return JSONResponse(status_code=404, content={"status": "error", "message": "Camera not found"})
    finally:
        db.close()

@router.post("/stop")
def stop_camera(control: CameraControl, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        target_cam = repo.get_by_id(control.camera_id)
        if target_cam:
            if target_cam.state == "STOPPED":
                return {"status": "success", "message": "Camera is already stopped."}
                
            target_cam.state = "STOPPED"
            db.commit()
            
            background_tasks.add_task(ffmpeg_manager.stop_stream, target_cam.id)
                
            edge_id = getattr(target_cam, 'edge_id', 'edge-01')
            publish_redis_command("stop_camera", target_cam.id, edge_id)
            
            return {"status": "success", "message": "Camera stop initiated on edge."}
        return JSONResponse(status_code=404, content={"status": "error", "message": "Camera not found"})
    finally:
        db.close()

@router.delete("/{cam_id}")
def delete_camera(cam_id: str, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        target_cam = repo.get_by_id(cam_id)
        if target_cam:
            # Send stop command if running
            if target_cam.state != "STOPPED":
                edge_id = getattr(target_cam, 'edge_id', 'edge-01')
                publish_redis_command("stop_camera", target_cam.id, edge_id)
            
            ffmpeg_manager.stop_stream(target_cam.id)
                
            db.delete(target_cam)
            db.commit()
            return {"status": "success", "message": "Camera deleted successfully."}
        return JSONResponse(status_code=404, content={"status": "error", "message": "Camera not found"})
    finally:
        db.close()

async def _batch_start_cameras(cameras):
    """Controlled concurrency logic to prevent blasting Redis simultaneously."""
    for cam in cameras:
        source = getattr(cam, 'source', cam.rtsp_url)
        source_type = getattr(cam, 'source_type', 'rtsp')
        edge_id = getattr(cam, 'edge_id', 'edge-01')
        
        if source:
            source = ffmpeg_manager.start_stream(cam.id, source)
            
        publish_redis_command("start_camera", cam.id, edge_id, source)
        await asyncio.sleep(0.05)  # 50ms pacing

@router.post("/start-all")
def start_all_cameras(background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        
        starting = []
        for cam in cameras:
            if cam.state not in ["Connecting/Offline", "Connected", "RUNNING"]:
                cam.state = "Connecting/Offline"
                starting.append(cam)
        
        db.commit()
        
        if starting:
            # Place in async queue to pace redis commands
            background_tasks.add_task(_batch_start_cameras, starting)
            
        return {"status": "success", "message": f"Start initiated for {len(starting)} cameras"}
    finally:
        db.close()

@router.post("/stop-all")
def stop_all_cameras(background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        for cam in cameras:
            if cam.state != "STOPPED":
                cam.state = "STOPPED"
                
                source_type = getattr(cam, 'source_type', 'rtsp')
                if source_type == 'video_file':
                    ffmpeg_manager.stop_stream(cam.id)
                    
                edge_id = getattr(cam, 'edge_id', 'edge-01')
                publish_redis_command("stop_camera", cam.id, edge_id)
        db.commit()
        return {"status": "success", "message": "Stop initiated for all cameras"}
    finally:
        db.close()

@router.post("/upload")
def upload_camera_video(file: UploadFile = File(...)):
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only video files are allowed.")
    
    safe_filename = os.path.basename(file.filename)
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "videos")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"status": "success", "file_path": file_path}

@router.get("")
def get_cameras():
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        return {
            "status": "success", 
            "cameras": [
                {
                    "id": c.id, 
                    "name": c.name, 
                    "rtsp_url": c.rtsp_url,
                    "source_type": getattr(c, 'source_type', 'rtsp'),
                    "source": getattr(c, 'source', c.rtsp_url),
                    "state": getattr(c, 'state', 'STOPPED'),
                    "edge_id": getattr(c, 'edge_id', 'edge-01')
                } for c in cameras
            ]
        }
    finally:
        db.close()

@router.get("/status")
def get_cameras_status():
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        status = {}
        for c in cameras:
            # Check Redis for real-time state from DeepStream (overrides DB)
            redis_state = redis_client.get(f"camera_state:{c.id}")
            if redis_state:
                status[c.id] = redis_state.decode() if isinstance(redis_state, bytes) else redis_state
            else:
                status[c.id] = getattr(c, 'state', 'Stopped')
        return status
    finally:
        db.close()
