from pydantic import BaseModel
from typing import List

class FireEventSchema(BaseModel):
    camera_id: str
    timestamp: float
    confidence: float
    fire_boxes: List[List[int]]
