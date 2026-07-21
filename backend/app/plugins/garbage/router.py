from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import SessionLocal
from typing import List

from app.plugins.garbage.repository import get_recent_garbage_events
from app.auth.dependencies import require_permissions

garbage_router = APIRouter(prefix="/api/garbage", tags=["Garbage Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@garbage_router.get("/events")
def get_garbage_events(db: Session = Depends(get_db)):
    """Fetch the latest garbage detection events for the UI."""
    events = get_recent_garbage_events(db, limit=50)
    
    result = []
    for e in events:
        snapshot_url = None
        if e.snapshot:
            snapshot_url = "/" + e.snapshot.full_frame_path
            
        result.append({
            "id": e.id,
            "camera_id": e.camera_id,
            "timestamp": e.timestamp,
            "category": e.category,
            "confidence": e.confidence,
            "duration_seconds": e.duration_seconds,
            "snapshot_url": snapshot_url
        })
        
    return {"events": result}
