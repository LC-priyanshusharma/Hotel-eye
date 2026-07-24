from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
import os
from sqlalchemy import text
from database.session import SessionLocal
from models.models import CameraEvent, Camera
from services.event_service import EventService
import random
import cv2
import threading
import time
import asyncio
from fastapi.middleware.cors import CORSMiddleware

from app.plugins.parking.router import parking_router
from app.plugins.attendance.router import attendance_router
from app.plugins.fire.router import fire_router
from app.plugins.visitor.router import router as visitor_router
from app.plugins.anpr.router import router as anpr_router
from app.auth.routes import router as auth_router
from app.auth.admin_routes import admin_router
from app.config_routes import config_router
from voice.api.routes import voice_router

app = FastAPI(title="AI CCTV Analytics API")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(config_router)

app.include_router(parking_router)
app.include_router(attendance_router)
app.include_router(fire_router)
app.include_router(visitor_router, prefix="/api/plugins")
app.include_router(anpr_router, prefix="/api/plugins")
app.include_router(voice_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since we need wildcard for dev, allow_credentials must be False
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    import threading
    from loguru import logger
    from core.camera_manager import camera_manager
    from config.config import config
    from database.persistence import DatabaseWorker
    from main import event_loop
    
    logger.info("Starting up FastAPI application and Camera Manager...")
    
    # 1. Start Database Worker
    app.state.db_worker = DatabaseWorker()
    app.state.db_worker.start()
    
    # 2. Start Global Workers
    camera_manager.start_global_workers()
    
    # 3. Start Camera Pipelines
    for url in config.camera_list:
        camera_manager.start_camera_pipeline(url)
        
    # 4. Start Event Router (Publishes to Redis)
    threading.Thread(target=event_loop, args=(camera_manager.result_queue,), daemon=True).start()

@app.on_event("shutdown")
def shutdown_event():
    from loguru import logger
    from core.camera_manager import camera_manager
    logger.info("Shutting down FastAPI application...")
    camera_manager.stop_all()
    if hasattr(app.state, "db_worker"):
        app.state.db_worker.stop()

os.makedirs("snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="snapshots"), name="snapshots")

LATEST_DATA = {}
EVENT_TTL_SECONDS = 1.0
DATA_LOCK = threading.Lock()
connected_websockets = set()

def update_global_state(packet: dict):
    import time
    cam_id = packet["camera_id"]
    now = time.time()
    
    with DATA_LOCK:
        if packet.get("is_gesture_synthetic", False):
            # Merge gesture events into existing packet to avoid overwriting YOLO events
            if cam_id in LATEST_DATA:
                LATEST_DATA[cam_id]["events"].update(packet["events"])
            return
            
        old_packet = LATEST_DATA.get(cam_id, {})
        cached_events = old_packet.get("_cached_events", {}).copy()
        
    new_events = packet.get("events", {})
    for plugin_name, events_list in new_events.items():
        if events_list:
            cached_events[plugin_name] = {"data": events_list, "ts": now}
            
    pruned_events = {}
    for plugin_name, cache_obj in list(cached_events.items()):
        if now - cache_obj["ts"] <= EVENT_TTL_SECONDS:
            pruned_events[plugin_name] = cache_obj["data"]
            
    if old_packet and "GestureDetectionPlugin" in old_packet.get("events", {}):
        pruned_events["GestureDetectionPlugin"] = old_packet["events"]["GestureDetectionPlugin"]

    packet["events"] = pruned_events
    packet["_cached_events"] = cached_events
    
    with DATA_LOCK:
        LATEST_DATA[cam_id] = packet

@app.get("/")
def health_check():
    return {"status": "running", "active_cameras": list(LATEST_DATA.keys())}

@app.get("/events")
def get_events():
    """Returns the latest historical events from the database."""
    events = EventService.get_latest_events()
    return JSONResponse(content=events)

@app.get("/analytics/dashboard")
def get_analytics_dashboard():
    stats = EventService.get_dashboard_stats(len(LATEST_DATA))
    return stats

@app.get("/stats/{camera_id:path}")
def get_camera_stats(camera_id: str):
    with DATA_LOCK:
        packet = LATEST_DATA.get(camera_id, {})
        events = packet.get("events", {})
        person_count = 0
        if "PeopleCountingPlugin" in events:
            for event in events["PeopleCountingPlugin"]:
                if event.get("event_type") == "PERSON_COUNT":
                    person_count = event["metadata"].get("current_people_in_frame", 0)
                    break
        return {"person_count": person_count}

class ManualEvent(BaseModel):
    camera_id: str
    event_type: str
    description: str
    
@app.post("/events/manual")
def post_manual_event(event: ManualEvent):
    from repositories.event_repository import EventRepository
    db = SessionLocal()
    try:
        repo = EventRepository(db)
        new_event = CameraEvent(
            camera_id=event.camera_id,
            events={
                "event_type": event.event_type,
                "description": event.description
            }
        )
        repo.add(new_event)
        return {"status": "success"}
    finally:
        db.close()

@app.get("/api/intrusions")
def get_intrusions():
    """Returns historical intrusion events with snapshots from the DB."""
    from repositories.event_repository import EventRepository
    db = SessionLocal()
    try:
        repo = EventRepository(db)
        events = repo.get_recent_events(limit=1000)
        
        intrusions = []
        for e in events:
            spatial_events = e.events.get("IntrusionDetectionPlugin", [])
            for event in spatial_events:
                if event.get("event_type") == "INTRUSION_DETECTED":
                    intrusions.append({
                        "id": e.id,
                        "camera_id": e.camera_id,
                        "timestamp": e.timestamp.isoformat(),
                        "track_id": event["metadata"].get("track_id"),
                        "snapshot": "/" + event.get("snapshot_path", ""),
                        "zone": event["metadata"].get("zone")
                    })
                
        return {"intrusions": intrusions}
    finally:
        db.close()

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Real-time WebSocket endpoint for the frontend."""
    await websocket.accept()
    connected_websockets.add(websocket)
    try:
        while True:
            # Gather state briefly
            with DATA_LOCK:
                # Create a shallow copy of LATEST_DATA keys/values to avoid RuntimeErrors
                snapshot = list(LATEST_DATA.items())
                
            response = {}
            for cam_id, packet in snapshot:
                response[cam_id] = {
                    "timestamp": packet["timestamp"],
                    "events": packet["events"],
                    "fps": packet.get("fps", 0.0)
                }
                
            # Push payload after encoding Pydantic models (outside the lock)
            encoded_response = jsonable_encoder(response)
            
            try:
                await websocket.send_json(encoded_response)
            except Exception:
                # If send_json fails, the client is dead. Break to disconnect.
                break
            
            # Target 10 FPS updates for the UI
            await asyncio.sleep(0.1) 
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

async def generate_mjpeg(camera_id: str):
    """Generator for MJPEG stream with Fast-Drop and Quality tuning."""
    import asyncio
    last_ts = 0
    while True:
        with DATA_LOCK:
            packet = LATEST_DATA.get(camera_id)
        
        if packet is None or packet.get("timestamp", 0) == last_ts:
            await asyncio.sleep(0.05) # Wait for a new frame asynchronously
            continue
            
        last_ts = packet.get("timestamp", 0)
            
        result = packet["detections"]
        
        import torch
        import cv2
        
        if "hlo.mp4" in camera_id:
            annotated_frame = packet["frame"].copy()
        else:
            annotated_frame = result.plot(labels=False, conf=False)
        
        # Override tracker IDs to just show 1, 2, 3... for the people currently in the frame
        if hasattr(result, 'boxes') and result.boxes is not None and getattr(result.boxes, 'is_track', False) and "hlo.mp4" not in camera_id:
            global CAMERA_ID_MAPS, CAMERA_AVAILABLE_IDS
            if 'CAMERA_ID_MAPS' not in globals():
                global CAMERA_ID_MAPS, CAMERA_AVAILABLE_IDS
                CAMERA_ID_MAPS = {}
                CAMERA_AVAILABLE_IDS = {}
                
            if camera_id not in CAMERA_ID_MAPS:
                CAMERA_ID_MAPS[camera_id] = {}
                CAMERA_AVAILABLE_IDS[camera_id] = set(range(1, 10000))
                
            cam_map = CAMERA_ID_MAPS[camera_id]
            cam_avail = CAMERA_AVAILABLE_IDS[camera_id]
            current_track_ids = result.boxes.id.cpu().numpy().tolist()
            
            local_ids = []
            for tid in current_track_ids:
                if tid not in cam_map:
                    sid = min(cam_avail)
                    cam_avail.remove(sid)
                    cam_map[tid] = sid
                local_ids.append(cam_map[tid])
                
            for tid in list(cam_map.keys()):
                if tid not in current_track_ids:
                    cam_avail.add(cam_map.pop(tid))
                    
            # Draw labels manually using OpenCV
            for box, sid in zip(result.boxes.xyxy.cpu().numpy(), local_ids):
                x1, y1, x2, y2 = map(int, box)
                label = f"id {sid}"
                # Draw small background rectangle for text
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated_frame, (x1, y1 - h - 10), (x1 + w + 10, y1), (255, 50, 50), -1)
                cv2.putText(annotated_frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw Gesture Landmarks if available
        if "GestureDetectionPlugin" in packet["events"]:
            gesture_data = packet["events"]["GestureDetectionPlugin"]
            for hand in gesture_data.get("gesture_events", []):
                landmarks = hand.get("landmarks", [])
                if landmarks:
                    import mediapipe as mp
                    from mediapipe.framework.formats import landmark_pb2
                    
                    mp_drawing = mp.solutions.drawing_utils
                    mp_hands = mp.solutions.hands
                    
                    hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                    hand_landmarks_proto.landmark.extend([
                        landmark_pb2.NormalizedLandmark(x=lm["x"], y=lm["y"], z=lm["z"]) 
                        for lm in landmarks
                    ])
                    
                    mp_drawing.draw_landmarks(
                        annotated_frame,
                        hand_landmarks_proto,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(255, 105, 180), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(255, 105, 180), thickness=2)
                    )
                        
        # Draw declarative UI from New Detection Plugins
        for plugin_name, events in packet["events"].items():
            if isinstance(events, list): # New plugins return lists of DetectionEvent dicts
                for event in events:
                    metadata = event.get("metadata", {})
                    drawings = metadata.get("drawings", [])
                    for draw in drawings:
                        if draw["type"] == "rect":
                            x1, y1, x2, y2 = draw["coords"]
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thick)
                        elif draw["type"] == "text":
                            x, y = draw["coords"]
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            scale = draw.get("scale", 0.7)
                            text = draw.get("text", "")
                            cv2.putText(annotated_frame, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)
                        elif draw["type"] == "poly":
                            import numpy as np
                            pts = np.array(draw["coords"], np.int32).reshape((-1, 1, 2))
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            cv2.polylines(annotated_frame, [pts], isClosed=True, color=color, thickness=thick)
                            
        # Always draw the currently configured Intrusion Zone for this camera
        if "hlo.mp4" not in camera_id:
            from config.config import config
            zone_coords = config.get_zone_for_camera(camera_id)
            if zone_coords:
                import numpy as np
                pts = np.array(zone_coords, np.int32).reshape((-1, 1, 2))
                # Draw semi-transparent overlay or just solid lines. We will draw red lines.
                cv2.polylines(annotated_frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
                cv2.putText(annotated_frame, "Restricted Zone", (zone_coords[0][0], zone_coords[0][1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                            
        # Reduce JPEG quality to 70 for 60% bandwidth savings (ECC Fast-Drop principle)
        ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ret:
            time.sleep(0.05)
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Yield to event loop, rate limited naturally by inference speed
        time.sleep(0.01)

@app.get("/video")
def video_feed(camera_id: str):
    """
    MJPEG streaming endpoint.
    Usage: /video?camera_id=rtsp://...
    """
    return StreamingResponse(generate_mjpeg(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/report/pdf")
def get_report_pdf():
    # Dummy PDF endpoint
    return JSONResponse(content={"status": "not implemented"}, status_code=404)

class CameraInfo(BaseModel):
    name: str
    rtsp_url: str
    
@app.post("/api/cameras")
def post_camera(camera: CameraInfo):
    from core.camera_manager import camera_manager
    from config.config import config
    import uuid
    
    # 1. Persist to Database
    from repositories.camera_repository import CameraRepository
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        # Generate a unique ID if needed or use URL hash
        cam_id = str(uuid.uuid4())
        
        # Check if already exists
        existing = repo.get_by_url(camera.rtsp_url)
        if not existing:
            new_cam = Camera(
                id=cam_id,
                name=camera.name,
                rtsp_url=camera.rtsp_url,
                active=True
            )
            repo.add(new_cam)
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        db.close()
    
    # 2. Update the running pipeline
    camera_manager.start_camera_pipeline(camera.rtsp_url)
    
    # 3. Update the config in memory so it's included in next /api/config save
    if not isinstance(config.CAMERA_URLS, str):
        config.CAMERA_URLS = camera.rtsp_url
    else:
        current_urls = [u.strip() for u in config.CAMERA_URLS.split(",") if u.strip()]
        if camera.rtsp_url not in current_urls:
            current_urls.append(camera.rtsp_url)
            config.CAMERA_URLS = ",".join(current_urls)
            
    # Also update the parsed list
    if camera.rtsp_url not in config.camera_list:
        config.camera_list.append(camera.rtsp_url)
        
    return {"status": "success", "camera": camera.model_dump()}

@app.get("/api/cameras")
def get_cameras():
    from repositories.camera_repository import CameraRepository
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        return {
            "status": "success", 
            "cameras": [
                {"id": c.id, "name": c.name, "rtsp_url": c.rtsp_url} for c in cameras
            ]
        }
    finally:
        db.close()

@app.get("/cameras/status")
def get_cameras_status():
    from core.camera_manager import camera_manager
    return camera_manager.get_status()

@app.get("/api/system/ip")
def get_system_ip():
    import socket
    try:
        # Create a dummy socket to determine the local IP used for outbound connections
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't actually connect to 8.8.8.8, it just helps the OS determine the route
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return {"ip": local_ip}
    except Exception as e:
        return {"ip": "127.0.0.1"}

# AI Agent Chat Endpoint
class ChatRequest(BaseModel):
    message: str
    camera_id: str = ""

@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    try:
        from agents.chat_agent import agent
        response = agent.chat(req.message, req.camera_id)
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return {"response": f"Sorry, I encountered an error: {str(e)}"}
