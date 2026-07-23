from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class WatchlistBase(BaseModel):
    plate_number: str
    list_type: str
    priority: int = 0
    notification_rules: Optional[Dict[str, Any]] = None
    expiry: Optional[float] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

class WatchlistCreate(WatchlistBase):
    pass

class WatchlistUpdate(BaseModel):
    plate_number: Optional[str] = None
    list_type: Optional[str] = None
    priority: Optional[int] = None
    notification_rules: Optional[Dict[str, Any]] = None
    expiry: Optional[float] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

class WatchlistResponse(WatchlistBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class ANPREventResponse(BaseModel):
    id: str
    event_type: str
    plate_number: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: float
    camera_id: str
    track_id: Optional[str] = None
    recognition_time_ms: Optional[float] = None
    ocr_confidence: Optional[float] = None
    detection_confidence: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True

class PlateHistoryResponse(BaseModel):
    id: str
    plate_number: str
    confidence: float
    timestamp: float
    camera_id: str
    track_id: Optional[str] = None
    vehicle_snapshot: Optional[str] = None
    plate_snapshot: Optional[str] = None
    direction: Optional[str] = None
    lane: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True

class PlateStatisticsResponse(BaseModel):
    id: str
    date_bucket: str
    camera_id: str
    total_detections: int
    unique_plates: int
    watchlist_matches: int
    metrics_json: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True
