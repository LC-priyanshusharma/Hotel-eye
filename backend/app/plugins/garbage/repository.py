from sqlalchemy.orm import Session
from app.plugins.garbage.models import GarbageEvent, GarbageSnapshot, GarbageAnalytics
from app.plugins.garbage.schemas import GarbageEventCreate, GarbageSnapshotCreate
import datetime

def create_garbage_event(db: Session, event: GarbageEventCreate, snapshot: GarbageSnapshotCreate = None) -> GarbageEvent:
    db_event = GarbageEvent(
        camera_id=event.camera_id,
        timestamp=event.timestamp,
        category=event.category,
        confidence=event.confidence,
        duration_seconds=event.duration_seconds,
        zone_polygon=event.zone_polygon
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    if snapshot:
        db_snapshot = GarbageSnapshot(
            event_id=db_event.id,
            full_frame_path=snapshot.full_frame_path,
            crop_path=snapshot.crop_path
        )
        db.add(db_snapshot)
        db.commit()
        
    return db_event

def get_recent_garbage_events(db: Session, limit: int = 100):
    return db.query(GarbageEvent).order_by(GarbageEvent.timestamp.desc()).limit(limit).all()
