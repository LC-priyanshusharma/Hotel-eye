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
    # MOCK DATA FOR VIDEO DEMO
    import time
    now_ts = time.time()
    mock_events = []
    for i in range(8):
        mock_events.append({
            "id": 5000 + i,
            "camera_id": f"Warehouse Zone {i % 3 + 1}",
            "timestamp": now_ts - (i * 12),
            "fire_boxes": [[100 + i*5, 150, 200, 250, 0.92 + (i*0.01)]],
            "snapshot_file": None
        })
    return {"events": mock_events}
