from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from sqlalchemy import text
from database.session import SessionLocal
from models.models import CameraEvent
from services.event_service import EventService
import random
import cv2
import threading
import time
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.plugins.garbage.schemas import GarbageEventCreate, GarbageSnapshotCreate
from app.plugins.garbage.repository import create_garbage_event
from app.plugins.garbage.router import garbage_router
from app.plugins.queue.router import queue_router
from app.plugins.parking.router import parking_router
from app.plugins.attendance.router import attendance_router
from app.plugins.fire.router import fire_router
from app.plugins.visitor.router import router as visitor_router
from app.auth.routes import router as auth_router
from app.auth.admin_routes import admin_router
from app.config_routes import config_router

app = FastAPI(title="AI CCTV Analytics API")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(config_router)
app.include_router(garbage_router)
app.include_router(queue_router)
app.include_router(parking_router)
app.include_router(attendance_router)
app.include_router(fire_router)
app.include_router(visitor_router, prefix="/api/plugins")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since we need wildcard for dev, allow_credentials must be False
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="snapshots"), name="snapshots")

LATEST_DATA = {}
DATA_LOCK = threading.Lock()
connected_websockets = set()

def update_global_state(packet: dict):
    with DATA_LOCK:
        cam_id = packet["camera_id"]
        if packet.get("is_gesture_synthetic", False):
            # Merge gesture events into existing packet to avoid overwriting YOLO events
            if cam_id in LATEST_DATA:
                LATEST_DATA[cam_id]["events"].update(packet["events"])
        else:
            # For YOLO packets, we can replace or keep old gesture events
            # But YOLO packet is complete, so we replace it
            old_packet = LATEST_DATA.get(cam_id)
            LATEST_DATA[cam_id] = packet
            if old_packet and "GestureDetectionPlugin" in old_packet.get("events", {}):
                LATEST_DATA[cam_id]["events"]["GestureDetectionPlugin"] = old_packet["events"]["GestureDetectionPlugin"]

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
    db = SessionLocal()
    try:
        new_event = CameraEvent(
            camera_id=event.camera_id,
            events={
                "event_type": event.event_type,
                "description": event.description
            }
        )
        db.add(new_event)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()

@app.get("/api/intrusions")
def get_intrusions():
    """Returns historical intrusion events with snapshots from the DB."""
    db = SessionLocal()
    try:
        events = db.query(CameraEvent).order_by(CameraEvent.timestamp.desc()).limit(1000).all()
        
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
            # Gather state
            with DATA_LOCK:
                response = {}
                for cam_id, packet in LATEST_DATA.items():
                    response[cam_id] = {
                        "timestamp": packet["timestamp"],
                        "events": packet["events"],
                        "fps": packet.get("fps", 0.0)
                    }
            # Push payload
            await websocket.send_json(response)
            
            # Target 10 FPS updates for the UI
            await asyncio.sleep(0.1) 
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
    except Exception as e:
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
        
        annotated_frame = result.plot(labels=False, conf=False)
        
        # Override tracker IDs to just show 1, 2, 3... for the people currently in the frame
        if hasattr(result, 'boxes') and result.boxes is not None and getattr(result.boxes, 'is_track', False):
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
    
@app.post("/cameras")
def post_camera(camera: CameraInfo):
    return {"status": "success", "camera": camera.model_dump()}

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
