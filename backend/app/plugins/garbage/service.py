import time
import os
import cv2
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import Point, Polygon
from loguru import logger

from app.engine.base import DetectionEvent, TrackerContext
from app.plugins.garbage.config import garbage_config
from app.plugins.garbage.constants import GARBAGE_CLASS_NAMES

class GarbageDetectionService:
    def __init__(self):
        os.makedirs("snapshots/garbage", exist_ok=True)
        # Assuming we might have some ROI/Ignore zones configured globally or per-camera
        # We will mock fetching them here
        
    def get_roi_polygon(self, camera_id: str) -> Optional[Polygon]:
        # Implementation would fetch from DB/Config. Return None for full frame.
        return None
        
    def get_ignore_polygons(self, camera_id: str) -> List[Polygon]:
        # Implementation would fetch from DB/Config. 
        return []

    def validate_and_track(self, camera_id: str, boxes: Any, cls_ids: Any, track_ids: Any, 
                           frame: Any, timestamp: float, tracker_context: TrackerContext) -> List[DetectionEvent]:
        
        events = []
        if boxes is None or len(boxes) == 0:
            return events
            
        state = tracker_context.get_state("GarbageDetectionPlugin", camera_id)
        if "loitering" not in state:
            state["loitering"] = {}
        if "known_alerts" not in state:
            state["known_alerts"] = set()
            
        loitering_memory = state["loitering"]
        known_alerts = state["known_alerts"]
        
        current_frame_ids = set()
        
        roi_poly = self.get_roi_polygon(camera_id)
        ignore_polys = self.get_ignore_polygons(camera_id)
        
        # Iterating directly over zipped numpy arrays passed from the plugin
        for box, cls_id, conf, track_id in zip(boxes, cls_ids[0], cls_ids[1], track_ids):
            track_id = int(track_id)
            current_frame_ids.add(track_id)
            
            x1, y1, x2, y2 = box
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            center_point = Point(center_x, center_y)
            
            # Check ROI / Ignore Zones
            if roi_poly and not roi_poly.contains(center_point):
                continue
                
            ignored = any(ignore_poly.contains(center_point) for ignore_poly in ignore_polys)
            if ignored:
                continue
                
            # Dwell Time Tracking
            if track_id not in loitering_memory:
                loitering_memory[track_id] = timestamp
            else:
                dwell_time = timestamp - loitering_memory[track_id]
                
                if dwell_time >= garbage_config.GARBAGE_DWELL_TIME_SECONDS:
                    if track_id not in known_alerts:
                        known_alerts.add(track_id)
                        
                        category_name = GARBAGE_CLASS_NAMES.get(int(cls_id), "unknown garbage")
                        
                        event = DetectionEvent(
                            plugin_name="GarbageDetectionPlugin",
                            event_type="GARBAGE_DETECTED",
                            camera_id=camera_id,
                            timestamp=timestamp,
                            confidence=float(conf),
                            metadata={"category": category_name, "duration_seconds": dwell_time},
                            snapshot_path=None
                        )
                        events.append(event)
                        logger.warning(f"🗑️ Garbage Alert: {category_name} detected for {dwell_time:.1f}s on {camera_id}")
                        
        # Cleanup tracks that disappeared
        to_delete = [tid for tid in loitering_memory.keys() if tid not in current_frame_ids]
        for tid in to_delete:
            del loitering_memory[tid]
            
        to_delete_alerts = [tid for tid in known_alerts if tid not in current_frame_ids]
        for tid in to_delete_alerts:
            known_alerts.remove(tid)
            
        return events
