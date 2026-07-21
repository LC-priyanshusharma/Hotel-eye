from pydantic import BaseModel
from typing import List, Optional

class IntrusionEventSchema(BaseModel):
    camera_id: str
    timestamp: float
    confidence: float
    track_id: int
    snapshot_path: Optional[str] = None
    zone_coords: List[List[int]]
