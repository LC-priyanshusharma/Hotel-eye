from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from database.models.models import CameraEvent

fire_router = APIRouter(prefix="/api/fire", tags=["Fire Detection Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@fire_router.get("/events")
def get_fire_events(db: Session = Depends(get_db), limit: int = 50):
    events_query = db.query(CameraEvent).filter(
        CameraEvent.events.op("->")("FireDetectionPlugin") != None
    ).order_by(desc(CameraEvent.timestamp)).limit(limit).all()
    
    formatted_events = []
    for e in events_query:
        plugin_events = e.events.get("FireDetectionPlugin", [])
        for pe in plugin_events:
            if pe.get("event_type") == "FIRE_DETECTED":
                formatted_events.append({
                    "id": str(e.id),
                    "camera_id": e.camera_id,
                    "timestamp": e.timestamp.timestamp(),
                    "fire_boxes": pe.get("metadata", {}).get("fire_boxes", []),
                    "snapshot_file": pe.get("snapshot_path")
                })
    
    return {"events": formatted_events[:limit]}
