from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import shutil
import os

from database.session import SessionLocal
from database.models.models import Camera
from database.repositories.camera_repository import CameraRepository
from core.camera_manager import camera_manager
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/cameras", tags=["Cameras"], dependencies=[Depends(get_current_user)])

class CameraInfo(BaseModel):
    name: str
    rtsp_url: str = None # Legacy
    source_type: str = "rtsp"
    source: str = None

class CameraControl(BaseModel):
    camera_id: str

@router.post("")
def post_camera(camera: CameraInfo, background_tasks: BackgroundTasks):
    import uuid
    
    db = SessionLocal()
    is_update = False
    try:
        repo = CameraRepository(db)
        cam_id = str(uuid.uuid4())
        
        actual_source = camera.source if camera.source else camera.rtsp_url
        
        existing = repo.get_by_name(camera.name)
        if existing:
            cam_id = existing.id
            is_active = existing.active
            existing.rtsp_url = actual_source
            existing.source_type = camera.source_type
            existing.source = actual_source
            db.commit()
            is_update = True
        else:
            is_active = True
            new_cam = Camera(
                id=cam_id,
                name=camera.name,
                rtsp_url=actual_source,
                source_type=camera.source_type,
                source=actual_source,
                active=True
            )
            repo.add(new_cam)
            is_update = False
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()
    
    if is_update and is_active:
        background_tasks.add_task(camera_manager.restart_camera_pipeline, cam_id, camera.source_type, actual_source)
    else:
        background_tasks.add_task(camera_manager.start_camera_pipeline, cam_id, camera.source_type, actual_source)
    
    return {"status": "success", "camera": camera.model_dump()}

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
        db.commit()
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()
        
    background_tasks.add_task(camera_manager.restart_camera_pipeline, cam_id, camera.source_type, actual_source)
    return {"status": "success", "message": "Camera updated"}



@router.post("/start")
def start_camera(control: CameraControl, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        target_cam = repo.get_by_id(control.camera_id)
        if target_cam:
            source = getattr(target_cam, 'source', target_cam.rtsp_url)
            source_type = getattr(target_cam, 'source_type', 'rtsp')
            background_tasks.add_task(camera_manager.start_camera_pipeline, target_cam.id, source_type, source)
            return {"status": "success", "message": "Pipeline start initiated"}
        return JSONResponse(status_code=404, content={"status": "error", "message": "Camera not found"})
    finally:
        db.close()

@router.post("/stop")
def stop_camera(control: CameraControl, background_tasks: BackgroundTasks):
    background_tasks.add_task(camera_manager.stop_camera_pipeline, control.camera_id)
    return {"status": "success", "message": "Pipeline stop initiated"}

@router.post("/start-all")
def start_all_cameras(background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        for cam in cameras:
            source = getattr(cam, 'source', cam.rtsp_url)
            source_type = getattr(cam, 'source_type', 'rtsp')
            background_tasks.add_task(camera_manager.start_camera_pipeline, cam.id, source_type, source)
        return {"status": "success", "message": f"Start initiated for {len(cameras)} cameras"}
    finally:
        db.close()

@router.post("/stop-all")
def stop_all_cameras(background_tasks: BackgroundTasks):
    background_tasks.add_task(camera_manager.stop_all)
    return {"status": "success", "message": "Stop initiated for all cameras"}

@router.post("/upload")
def upload_camera_video(file: UploadFile = File(...)):
    # 1. Type Checking
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only video files are allowed.")
    
    # 2. Path Sanitization (prevent directory traversal)
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
                    "source": getattr(c, 'source', c.rtsp_url)
                } for c in cameras
            ]
        }
    finally:
        db.close()

@router.get("/status")
def get_cameras_status():
    return camera_manager.get_status()
