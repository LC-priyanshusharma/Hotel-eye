from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from models.models import CameraEvent

attendance_router = APIRouter(prefix="/api/attendance", tags=["Attendance Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@attendance_router.get("/stats")
def get_attendance_stats(db: Session = Depends(get_db)):
    """Fetch the latest attendance state and logs per camera."""
    events = db.query(CameraEvent).order_by(desc(CameraEvent.timestamp)).limit(200).all()
    
    attendance_data = {}
    for e in events:
        cam = e.camera_id
        if cam not in attendance_data:
            if "AttendanceDetectionPlugin" in e.events:
                a_events = e.events["AttendanceDetectionPlugin"]
                for a_evt in a_events:
                    if a_evt.get("event_type") == "ATTENDANCE_STATE":
                        meta = a_evt.get("metadata", {})
                        attendance_data[cam] = {
                            "timestamp": e.timestamp,
                            "authorized_employees_in_frame": meta.get("authorized_employees_in_frame", []),
                            "unauthorized_count": meta.get("unauthorized_count", 0),
                            "attendance_logs": meta.get("attendance_logs", [])
                        }
                        break
                        
    return {"current": attendance_data}
