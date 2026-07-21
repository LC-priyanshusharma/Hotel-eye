from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.session import SessionLocal
from typing import List, Dict, Any
from models.models import CameraEvent
import json

queue_router = APIRouter(prefix="/api/queue", tags=["Queue Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@queue_router.get("/stats")
def get_queue_stats(db: Session = Depends(get_db)):
    """Fetch the latest queue SMA predictions and lengths."""
    # We query the latest QUEUE_STATS from CameraEvent for each camera
    # Since CameraEvent is generic, we do a recent fetch and filter
    
    events = db.query(CameraEvent).order_by(desc(CameraEvent.timestamp)).limit(200).all()
    
    queue_data = {}
    for e in events:
        cam = e.camera_id
        if cam not in queue_data:
            if "QueueAnalyticsPlugin" in e.events:
                q_events = e.events["QueueAnalyticsPlugin"]
                for q_evt in q_events:
                    if q_evt.get("event_type") == "QUEUE_STATS":
                        meta = q_evt.get("metadata", {})
                        queue_data[cam] = {
                            "timestamp": e.timestamp,
                            "people_in_queue": meta.get("people_in_queue", 0),
                            "predicted_wait_seconds": meta.get("predicted_wait_seconds", 0.0)
                        }
                        break
                        
    # Format for charting
    history = []
    # Just sending the latest state per camera for the summary
    return {"current": queue_data, "history": history}

@queue_router.get("/history")
def get_queue_history(camera_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Fetch historical queue sizes and wait times for graphing."""
    events = db.query(CameraEvent).filter(CameraEvent.camera_id == camera_id).order_by(desc(CameraEvent.timestamp)).limit(500).all()
    
    history = []
    for e in reversed(events): # Oldest first for graphing
        if "QueueAnalyticsPlugin" in e.events:
            q_events = e.events["QueueAnalyticsPlugin"]
            for q_evt in q_events:
                if q_evt.get("event_type") == "QUEUE_STATS":
                    meta = q_evt.get("metadata", {})
                    history.append({
                        "time": e.timestamp.strftime("%H:%M:%S"),
                        "people": meta.get("people_in_queue", 0),
                        "wait": round(meta.get("predicted_wait_seconds", 0.0), 1)
                    })
                    break
                    
    # Downsample if too large
    if len(history) > limit:
        step = len(history) // limit
        history = history[::step]
        
    return {"history": history}
