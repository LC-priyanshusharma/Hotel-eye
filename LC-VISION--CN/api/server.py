from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from sqlalchemy import text
from db.session import SessionLocal
from db.models import CameraEvent
import random
import cv2
import threading
import time
import asyncio
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI CCTV Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, allow all
    allow_credentials=True,
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
    db = SessionLocal()
    try:
        known_cameras = db.query(CameraEvent.camera_id).distinct().all()
        result = []
        
        for (cam_id,) in known_cameras:
            # Fetch up to 200 to ensure we bypass Analytics Update spam
            cam_events = db.query(CameraEvent).filter(CameraEvent.camera_id == cam_id).order_by(CameraEvent.timestamp.desc()).limit(200).all()
            
            valid_cam_events = []
            last_desc = None
            for e in cam_events:
                event_type = e.events.get("event_type", "info")
                description = e.events.get("description", "Analytics Update")
                snapshot_file = e.events.get("snapshot_file", None)
                
                if "EnterpriseSafetyPlugin" in e.events:
                    active_alerts = e.events["EnterpriseSafetyPlugin"].get("active_alerts", [])
                    if "FIRE_DETECTED" in active_alerts:
                        event_type = "danger"
                        description = "Fire Detected"
                    elif "SMOKE_DETECTED" in active_alerts:
                        event_type = "danger"
                        description = "Smoke Detected"
                        
                if "WeaponDetectionPlugin" in e.events:
                    active_alerts = e.events["WeaponDetectionPlugin"].get("active_alerts", [])
                    new_snapshots = e.events["WeaponDetectionPlugin"].get("new_snapshots", [])
                    if "WEAPON_DETECTED" in active_alerts:
                        event_type = "danger"
                        description = "Weapon Detected"
                        if new_snapshots:
                            snapshot_file = new_snapshots[0]
                        
                if "SpatialAnalyticsPlugin" in e.events:
                    intrusions = e.events["SpatialAnalyticsPlugin"].get("new_intrusions", [])
                    if intrusions:
                        event_type = "warning"
                        description = "Zone Intrusion Detected"
                        snapshot_file = intrusions[0].get("snapshot")
                        
                if "IdentityAnalyticsPlugin" in e.events:
                    attendance = e.events["IdentityAnalyticsPlugin"].get("attendance_logs", [])
                    if attendance:
                        latest_log = attendance[-1]
                        action = latest_log.get("action")
                        emp = latest_log.get("employee")
                        description = f"{emp} {action}"
                        event_type = "success" if action == "CHECK IN" else "info"
                        
                if "PeopleCountingPlugin" in e.events and description == "Analytics Update":
                    # Only show person count if there's no higher priority event on this frame
                    count = e.events["PeopleCountingPlugin"].get("current_people_in_frame", 0)
                    if count > 0:
                        description = f"Person Count: {count}"
                        event_type = "info"
                        
                if "GestureDetectionPlugin" in e.events:
                    gesture_data = e.events["GestureDetectionPlugin"]
                    active_alerts = gesture_data.get("active_alerts", [])
                    if "HAND_RAISE_DETECTED" in active_alerts:
                        event_type = "info"
                        description = "Hand Raise Detected"
                        if gesture_data.get("snapshot_file"):
                            snapshot_file = "/" + gesture_data.get("snapshot_file")
                    elif "GESTURE_DETECTED" in active_alerts:
                        gesture_events = gesture_data.get("gesture_events", [])
                        if gesture_events:
                            top_gesture = gesture_events[0].get("gesture", "Unknown")
                            event_type = "info"
                            description = f"Gesture: {top_gesture}"
                            if gesture_data.get("snapshot_file"):
                                snapshot_file = "/" + gesture_data.get("snapshot_file")

                # Skip spammy analytics updates at the API level
                if description == "Analytics Update":
                    continue
                    
                # Deduplicate consecutive identical events to prevent starvation (e.g. 20 consecutive Smoke Detects)
                if description == last_desc:
                    continue
                last_desc = description

                valid_cam_events.append({
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "camera_id": e.camera_id,
                    "event_type": event_type,
                    "description": description,
                    "snapshot_file": snapshot_file
                })
                
                # Limit to top 15 valid, deduplicated events per camera
                if len(valid_cam_events) >= 15:
                    break
                    
            result.extend(valid_cam_events)

        # Sort the combined result by timestamp descending
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return JSONResponse(content=result)
    finally:
        db.close()

@app.get("/analytics/dashboard")
def get_analytics_dashboard():
    db = SessionLocal()
    critical_alerts = 0
    try:
        # Just grab the last 1000 events to estimate recent critical alerts
        events = db.query(CameraEvent).order_by(CameraEvent.timestamp.desc()).limit(1000).all()
        for e in events:
            if "EnterpriseSafetyPlugin" in e.events:
                active = e.events["EnterpriseSafetyPlugin"].get("active_alerts", [])
                if "FIRE_DETECTED" in active or "SMOKE_DETECTED" in active:
                    critical_alerts += 1
            if "WeaponDetectionPlugin" in e.events:
                active = e.events["WeaponDetectionPlugin"].get("active_alerts", [])
                if "WEAPON_DETECTED" in active:
                    critical_alerts += 1
    finally:
        db.close()

    return {
        "total_cameras": len(LATEST_DATA) or 1,
        "ai_enabled": len(LATEST_DATA) or 1,
        "critical_alerts": critical_alerts,
        "uptime": "99.9%",
        "system_health": {
            "cpu_usage": 45,
            "gpu_usage": 15,
            "ram_usage": 60,
            "storage_usage": 30,
            "network_bandwidth": 150
        }
    }

@app.get("/stats/{camera_id:path}")
def get_camera_stats(camera_id: str):
    with DATA_LOCK:
        packet = LATEST_DATA.get(camera_id, {})
        events = packet.get("events", {})
        person_count = 0
        if "PeopleCountingPlugin" in events:
            person_count = events["PeopleCountingPlugin"].get("person_count", 0)
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
        # We query the DB for camera_events where the SpatialAnalyticsPlugin returned new_intrusions
        # Since events is a JSONB column, we can do a raw SQL query or just fetch and filter in Python.
        # Let's do a simple fetch of the last 1000 events and filter in Python for broad DB compatibility (SQLite/PG).
        events = db.query(CameraEvent).order_by(CameraEvent.timestamp.desc()).limit(1000).all()
        
        intrusions = []
        for e in events:
            spatial_data = e.events.get("SpatialAnalyticsPlugin", {})
            new_intrusions = spatial_data.get("new_intrusions", [])
            for intrusion in new_intrusions:
                intrusions.append({
                    "id": e.id,
                    "camera_id": e.camera_id,
                    "timestamp": e.timestamp.isoformat(),
                    "track_id": intrusion.get("track_id"),
                    "snapshot": "/" + intrusion.get("snapshot"),
                    "zone": intrusion.get("zone")
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

def generate_mjpeg(camera_id: str):
    """Generator for MJPEG stream."""
    while True:
        with DATA_LOCK:
            packet = LATEST_DATA.get(camera_id)
        
        if packet is None:
            time.sleep(0.1)
            continue
            
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
        
        # Threat notification for smoke/fire on the live feed
        if "EnterpriseSafetyPlugin" in packet["events"]:
            safety_data = packet["events"]["EnterpriseSafetyPlugin"]
            active_alerts = safety_data.get("active_alerts", [])
            
            # Draw fire bounding boxes
            for (fx1, fy1, fx2, fy2) in safety_data.get("fire_boxes", []):
                cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 3)
                cv2.putText(annotated_frame, "FIRE", (fx1, fy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
            # Draw smoke bounding boxes
            for (sx1, sy1, sx2, sy2) in safety_data.get("smoke_boxes", []):
                cv2.rectangle(annotated_frame, (sx1, sy1), (sx2, sy2), (200, 200, 200), 2)
                cv2.putText(annotated_frame, "SMOKE", (sx1, sy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

            if "SMOKE_DETECTED" in active_alerts:
                cv2.putText(annotated_frame, "THREAT: SMOKE DETECTED", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
            if "FIRE_DETECTED" in active_alerts:
                cv2.putText(annotated_frame, "THREAT: FIRE DETECTED", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)

        if "WeaponDetectionPlugin" in packet["events"]:
            weapon_data = packet["events"]["WeaponDetectionPlugin"]
            active_alerts = weapon_data.get("active_alerts", [])
            for (wx1, wy1, wx2, wy2) in weapon_data.get("weapon_boxes", []):
                cv2.rectangle(annotated_frame, (int(wx1), int(wy1)), (int(wx2), int(wy2)), (0, 165, 255), 3) # Orange
                cv2.putText(annotated_frame, "WEAPON", (int(wx1), int(wy1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            if "WEAPON_DETECTED" in active_alerts:
                cv2.putText(annotated_frame, "THREAT: WEAPON DETECTED", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 4)

        if "GestureDetectionPlugin" in packet["events"]:
            gesture_data = packet["events"]["GestureDetectionPlugin"]
            for h in gesture_data.get("gesture_events", []):
                hx1, hy1, hx2, hy2 = h["bbox"]
                gesture_name = h["gesture"]
                cv2.rectangle(annotated_frame, (int(hx1), int(hy1)), (int(hx2), int(hy2)), (255, 0, 255), 3) # Magenta
                cv2.putText(annotated_frame, f"GESTURE: {gesture_name}", (int(hx1), int(hy1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            time.sleep(0.1)
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Throttle stream output to save bandwidth
        time.sleep(0.1)

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
