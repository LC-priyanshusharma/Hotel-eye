from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from models.models import CameraEvent

fire_router = APIRouter(prefix="/api/fire", tags=["Fire Detection Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@fire_router.get("/events")
def get_fire_events(db: Session = Depends(get_db), limit: int = 50):
    """Fetch the latest fire detection events."""
    # To find fire events, we can query recent camera events and filter
    # Ideally this would be indexed or split, but since CameraEvent contains a JSON blob,
    # we filter in python for now (acceptable for limited rows, but in production we'd use a JSONB query).
    
    events = db.query(CameraEvent).order_by(desc(CameraEvent.timestamp)).limit(500).all()
    
    fire_logs = []
    for e in events:
        if "FireDetectionPlugin" in e.events:
            f_events = e.events["FireDetectionPlugin"]
            for f_evt in f_events:
                if f_evt.get("event_type") == "FIRE_DETECTED":
                    meta = f_evt.get("metadata", {})
                    fire_logs.append({
                        "id": e.id,
                        "camera_id": e.camera_id,
                        "timestamp": e.timestamp,
                        "fire_boxes": meta.get("fire_boxes", [])
                    })
                    break
                    
        if len(fire_logs) >= limit:
            break
            
    return {"events": fire_logs}
