from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from database.models.models import CameraEvent

attendance_router = APIRouter(prefix="/api/attendance", tags=["Attendance Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@attendance_router.get("/stats")
def get_attendance_stats(db: Session = Depends(get_db)):
    events = db.query(CameraEvent).filter(
        CameraEvent.events.op("->")("AttendancePlugin") != None
    ).order_by(desc(CameraEvent.timestamp)).limit(50).all()
    
    logs_by_cam = {}
    for e in events:
        if e.camera_id not in logs_by_cam:
            logs_by_cam[e.camera_id] = []
        plugin_events = e.events.get("AttendancePlugin", [])
        for pe in plugin_events:
            if pe.get("event_type") in ["CHECK IN", "CHECK OUT", "UNAUTHORIZED"]:
                logs_by_cam[e.camera_id].append({
                    "time": e.timestamp.timestamp(),
                    "action": pe.get("event_type"),
                    "employee": pe.get("metadata", {}).get("person_name", "Unknown Person")
                })
    
    # We rely on WebSocket for live state, this just provides recent logs per camera
    # We will format it to match the expected schema but leave live arrays empty.
    result = {}
    for cam, logs in logs_by_cam.items():
        result[cam] = {
            "authorized_employees_in_frame": [], # Handled by WebSocket on frontend
            "unauthorized_count": 0,             # Handled by WebSocket on frontend
            "attendance_logs": logs[:10]
        }
    return {"current": result}
