import os
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from app.plugins.visitor.schemas import VisitorResponse, VisitResponse, VisitorEventResponse, VisitorRegisterRequest, PaginatedVisitorResponse
from app.plugins.visitor.models import Visitor, Visit, VisitorEvent
from pydantic import BaseModel
from datetime import datetime
from config.config import config
from detection.face_factory import FaceFactory

import uuid
import base64
import time

router = APIRouter(prefix="/visitor", tags=["Visitor Management"])

def decode_base64_image(b64_str: str):
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def get_next_visitor_id(db: Session, prefix: str = "VIS") -> str:
    # Get all visitor IDs that start with the prefix
    visitors = db.query(Visitor.visitor_id).filter(Visitor.visitor_id.like(f"{prefix}-%")).all()
    
    max_num = 0
    for (vid,) in visitors:
        try:
            # e.g., "VIS-0001" -> 1
            num_part = vid.split("-")[1]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            # Ignore legacy UUIDs or malformed IDs
            pass
            
    next_num = max_num + 1
    return f"{prefix}-{next_num:04d}"

# Global Singleton to avoid loading model on every request
_global_detector = None

def get_detector():
    global _global_detector
    if _global_detector is None:
        _global_detector = FaceFactory.create(config.FACE_BACKEND)
    return _global_detector

@router.post("/register", response_model=VisitorResponse)
def register_visitor(request: VisitorRegisterRequest, db: Session = Depends(get_db)):
    detector = get_detector()
    
    # Process images
    images = [
        decode_base64_image(request.photo_front),
        decode_base64_image(request.photo_left),
        decode_base64_image(request.photo_right)
    ]
    
    embeddings = []
    best_image = None
    best_size = 0
    
    for img in images:
        if img is not None:
            faces = detector.detect_and_extract(img)
            if faces and faces[0].get("embedding") is not None:
                embeddings.append(faces[0]["embedding"])
                
                # Keep the largest face as the profile photo
                bbox = faces[0].get("bbox")
                if bbox is not None:
                    size = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    if size > best_size:
                        best_size = size
                        best_image = img
                        
    if not embeddings:
        raise HTTPException(status_code=400, detail="Could not detect a clear face in any of the provided photos.")
        
    # Average the embeddings for higher accuracy across angles
    avg_embedding = np.mean(embeddings, axis=0)
    
    # Save the best image
    os.makedirs("snapshots/visitors", exist_ok=True)
    role = request.role.upper() if request.role else "VISITOR"
    prefix = "EMP" if role == "EMPLOYEE" else "VIS"
    visitor_uid = get_next_visitor_id(db, prefix)
    photo_path = f"snapshots/visitors/{visitor_uid}.jpg"
    if best_image is not None:
        cv2.imwrite(photo_path, best_image)
    
    new_visitor = Visitor(
        visitor_id=visitor_uid,
        name=request.name,
        email=request.email,
        photo=photo_path,
        face_embedding=avg_embedding.tolist(),
        status="REGISTERED",
        role=role
    )
    db.add(new_visitor)
    db.commit()
    db.refresh(new_visitor)
    
    # Emit WebSocket Event so the Dashboard updates in real time!
    from api.server import LATEST_DATA, DATA_LOCK
    with DATA_LOCK:
        if "SYSTEM" not in LATEST_DATA:
            LATEST_DATA["SYSTEM"] = {"timestamp": time.time(), "events": {}, "fps": 0}
        
        if "VisitorPlugin" not in LATEST_DATA["SYSTEM"]["events"]:
            LATEST_DATA["SYSTEM"]["events"]["VisitorPlugin"] = []
            
        LATEST_DATA["SYSTEM"]["events"]["VisitorPlugin"].append({
            "plugin": "VisitorPlugin",
            "event_type": VisitorEventType.EMPLOYEE_REGISTERED.value if role == "EMPLOYEE" else VisitorEventType.VISITOR_REGISTERED.value,
            "camera_id": "SYSTEM",
            "timestamp": new_visitor.created_at.timestamp() if new_visitor.created_at else time.time(),
            "confidence": 1.0,
            "metadata": {
                "visitor_id": new_visitor.visitor_id,
                "name": new_visitor.name
            }
        })
        LATEST_DATA["SYSTEM"]["timestamp"] = time.time()
        
    return new_visitor

class BulkDeleteRequest(BaseModel):
    start_time: datetime
    end_time: datetime

@router.delete("/bulk", response_model=dict)
def bulk_delete_visitors(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    """Deletes all visitors created between start_time and end_time, cascading to their visits and events."""
    # Find all visitors within the time range
    visitors_to_delete = db.query(Visitor).filter(
        Visitor.created_at >= request.start_time,
        Visitor.created_at <= request.end_time
    ).all()
    
    deleted_count = 0
    for v in visitors_to_delete:
        # 1. Delete associated visitor events
        db.query(VisitorEvent).filter(VisitorEvent.visitor_id == v.visitor_id).delete()
        
        # 2. Delete associated visits
        db.query(Visit).filter(Visit.visitor_id == v.visitor_id).delete()
        
        # 3. Delete visitor photo if it exists locally
        if v.photo and os.path.exists(v.photo):
            try:
                os.remove(v.photo)
            except Exception:
                pass
                
        # 4. Delete the visitor
        db.delete(v)
        deleted_count += 1
        
    db.commit()
    return {"status": "success", "deleted_count": deleted_count}

@router.get("", response_model=PaginatedVisitorResponse)
def get_visitors(db: Session = Depends(get_db), limit: int = 50, page: int = 1, role: str = None):
    offset = (page - 1) * limit
    
    query = db.query(Visitor).filter(Visitor.status == "REGISTERED")
    if role:
        query = query.filter(Visitor.role == role.upper())
        
    total = query.count()
    
    data = query.order_by(Visitor.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/{visitor_id}", response_model=VisitorResponse)
def get_visitor(visitor_id: str, db: Session = Depends(get_db)):
    v = db.query(Visitor).filter(Visitor.visitor_id == visitor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return v

@router.get("/{visitor_id}/history", response_model=List[VisitResponse])
def get_visitor_history(visitor_id: str, db: Session = Depends(get_db), limit: int = 50):
    return db.query(Visit).filter(Visit.visitor_id == visitor_id).order_by(Visit.entry_time.desc()).limit(limit).all()

@router.get("/events/all", response_model=List[VisitorEventResponse])
def get_visitor_events(db: Session = Depends(get_db), limit: int = 50):
    return db.query(VisitorEvent).order_by(VisitorEvent.timestamp.desc()).limit(limit).all()

def rebuild_embeddings_task(db: Session):
    detector = get_detector()
    visitors_without_embedding = db.query(Visitor).filter(Visitor.face_embedding.is_(None)).filter(Visitor.photo.isnot(None)).all()
    
    for v in visitors_without_embedding:
        try:
            # Assuming 'photo' is a local path. E.g., 'snapshots/google_forms/img123.jpg'
            # If it's a URL, you'd need to requests.get it. Assuming local per instructions.
            if os.path.exists(v.photo):
                img = cv2.imread(v.photo)
                if img is not None:
                    faces = detector.detect_and_extract(img)
                    if faces and faces[0].get("embedding") is not None:
                        v.face_embedding = faces[0]["embedding"].tolist()
                        db.commit()
        except Exception as e:
            print(f"Failed to generate embedding for {v.visitor_id}: {e}")

@router.post("/rebuild-embeddings")
def trigger_embedding_rebuild(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Scans the database for visitors with a photo but no embedding, 
    and generates the 512D face embeddings in the background.
    """
    background_tasks.add_task(rebuild_embeddings_task, db)
    return {"status": "Rebuild task started in background."}
