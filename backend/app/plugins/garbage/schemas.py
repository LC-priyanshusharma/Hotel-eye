from pydantic import BaseModel
from typing import List, Optional, Dict

class GarbageEventCreate(BaseModel):
    camera_id: str
    timestamp: float
    category: str
    confidence: float
    duration_seconds: float
    zone_polygon: Optional[List[List[float]]] = None
    
class GarbageSnapshotCreate(BaseModel):
    full_frame_path: str
    crop_path: Optional[str] = None

class GarbageEventResponse(BaseModel):
    id: int
    camera_id: str
    timestamp: float
    category: str
    confidence: float
    duration_seconds: float
    snapshot_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class GarbageAnalyticsResponse(BaseModel):
    camera_id: str
    date_bucket: str
    total_events: int
    category_breakdown: Dict[str, int]
    
    class Config:
        from_attributes = True
