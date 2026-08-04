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
def get_attendance_stats():
    # MOCK DATA FOR VIDEO DEMO
    import time
    now_ts = time.time()
    
    logs = [
        {"time": now_ts - 300, "action": "CHECK IN", "employee": "John Doe"},
        {"time": now_ts - 900, "action": "CHECK IN", "employee": "Sarah Smith"},
        {"time": now_ts - 120, "action": "CHECK IN", "employee": "Michael Chen"},
        {"time": now_ts - 1800, "action": "CHECK OUT", "employee": "Emily Davis"},
        {"time": now_ts - 60, "action": "UNKNOWN", "employee": "Unknown Person"},
    ]
    
    mock_data = {
        "Main Entrance (Cam 1)": {
            "timestamp": now.isoformat() + "Z",
            "authorized_employees_in_frame": [
                {"id": "EMP-001", "name": "John Doe", "confidence": 0.98},
                {"id": "EMP-099", "name": "Michael Chen", "confidence": 0.95}
            ],
            "unauthorized_count": 1,
            "attendance_logs": logs
        },
        "Back Door (Cam 2)": {
            "timestamp": now.isoformat() + "Z",
            "authorized_employees_in_frame": [],
            "unauthorized_count": 0,
            "attendance_logs": []
        }
    }
    return {"current": mock_data}
