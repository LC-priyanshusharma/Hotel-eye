from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from models.models import CameraEvent

parking_router = APIRouter(prefix="/api/parking", tags=["Parking Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@parking_router.get("/stats")
def get_parking_stats(db: Session = Depends(get_db)):
    """Fetch the latest parking spot statistics per camera."""
    events = db.query(CameraEvent).order_by(desc(CameraEvent.timestamp)).limit(200).all()
    
    parking_data = {}
    for e in events:
        cam = e.camera_id
        if cam not in parking_data:
            if "ParkingAnalyticsPlugin" in e.events:
                p_events = e.events["ParkingAnalyticsPlugin"]
                for p_evt in p_events:
                    if p_evt.get("event_type") == "PARKING_STATS":
                        meta = p_evt.get("metadata", {})
                        parking_data[cam] = {
                            "timestamp": e.timestamp,
                            "total_spots": meta.get("total_spots", 0),
                            "occupied_spots": meta.get("occupied_spots", 0),
                            "available_spots": meta.get("available_spots", 0),
                            "spot_status": meta.get("spot_status", []),
                            "vehicle_count": meta.get("vehicle_count", 0)
                        }
                        break
                        
    return {"current": parking_data}
