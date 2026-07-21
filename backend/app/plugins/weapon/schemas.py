from pydantic import BaseModel
from typing import List, Optional

class WeaponEventSchema(BaseModel):
    camera_id: str
    timestamp: float
    confidence: float
    weapon_boxes: List[List[int]]
    snapshot_path: Optional[str] = None
