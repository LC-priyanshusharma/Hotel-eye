from typing import List, Dict, Any
from loguru import logger
import time
from shapely.geometry import Point, Polygon

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
from config.config import config

class QueueAnalyticsPlugin(BaseDetectionPlugin):
    """
    Handles Queue Length and Waiting Time Prediction.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # Maps camera_id -> { track_id: enter_timestamp }
        self.queue_memory: Dict[str, Dict[int, float]] = {}
        # Stores recent wait times (in seconds) for SMA prediction
        self.recent_wait_times: List[float] = []
        logger.info("Initialized QueueAnalyticsPlugin")

    @property
    def plugin_name(self) -> str:
        return "QueueAnalyticsPlugin"

    def get_required_classes(self) -> List[int]:
        # Person
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        events = []
        
        if camera_id not in self.queue_memory:
            self.queue_memory[camera_id] = {}
            
        queue_coords = config.get_queue_zone_for_camera(camera_id)
        if not queue_coords:
            return events
            
        queue_poly = Polygon(queue_coords)
        
        active_in_queue = []
        current_frame_ids = set()
        
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None and getattr(frame_data.detections.boxes, 'id', None) is not None:
            boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            track_ids = frame_data.detections.boxes.id.cpu().numpy()
            
            for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                if int(cls_id) != 0:
                    continue
                    
                track_id = int(track_id)
                current_frame_ids.add(track_id)
                
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                bottom_y = y2
                feet_point = Point(center_x, bottom_y)
                
                if queue_poly.contains(feet_point):
                    active_in_queue.append(track_id)
                    if track_id not in self.queue_memory[camera_id]:
                        self.queue_memory[camera_id][track_id] = timestamp
                else:
                    if track_id in self.queue_memory[camera_id]:
                        enter_time = self.queue_memory[camera_id][track_id]
                        time_spent = timestamp - enter_time
                        if time_spent > 2.0:
                            self.recent_wait_times.append(time_spent)
                            if len(self.recent_wait_times) > 10:
                                self.recent_wait_times.pop(0)
                        del self.queue_memory[camera_id][track_id]
        
        memory = self.queue_memory[camera_id]
        to_delete = [tid for tid in memory.keys() if tid not in current_frame_ids]
        for tid in to_delete:
            del memory[tid]
            
        predicted_wait = 0.0
        if self.recent_wait_times:
            predicted_wait = sum(self.recent_wait_times) / len(self.recent_wait_times)
            
        drawings = []
        drawings.append({
            "type": "poly",
            "coords": queue_coords,
            "color": [255, 255, 0],
            "thickness": 2
        })
        
        # We always emit an event so the queue stats can be updated
        event = DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="QUEUE_STATS",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "queue_length": len(active_in_queue),
                "predicted_wait_time_seconds": round(predicted_wait, 1),
                "drawings": drawings
            }
        )
        events.append(event)
            
        return events
