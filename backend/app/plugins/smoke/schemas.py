from pydantic import BaseModel
from typing import List, Tuple

class SmokeDrawing(BaseModel):
    type: str  # "rect" or "text"
    coords: List[int] # [x1, y1, x2, y2] for rect, [x, y] for text
    color: Tuple[int, int, int]
    thickness: int = 2
    text: str = ""
    scale: float = 0.7

class SmokeEventSchema(BaseModel):
    camera_id: str
    timestamp: float
    confidence: float
    smoke_boxes: List[List[int]]
