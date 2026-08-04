from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from database.models.models import CameraEvent

parking_router = APIRouter(prefix="/api/parking", tags=["Parking Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@parking_router.get("/stats")
def get_parking_stats():
    # MOCK DATA FOR VIDEO DEMO
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    
    mock_data = {
        "Parking Lot Alpha (Cam 1)": {
            "timestamp": now,
            "total_spots": 50,
            "occupied_spots": 32,
            "available_spots": 18,
            "spot_status": [(i < 32) for i in range(50)],
            "vehicle_count": 35
        },
        "Underground Level B (Cam 2)": {
            "timestamp": now,
            "total_spots": 120,
            "occupied_spots": 115,
            "available_spots": 5,
            "spot_status": [(i < 115) for i in range(120)],
            "vehicle_count": 118
        }
    }
    return {"current": mock_data}
