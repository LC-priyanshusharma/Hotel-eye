from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class PeopleCountingPlugin(BaseDetectionPlugin):
    """
    Counts the total number of unique people seen by inspecting the ByteTrack IDs.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.unique_ids = set()
        logger.info("Initialized PeopleCountingPlugin")

    @property
    def plugin_name(self) -> str:
        return "PeopleCountingPlugin"

    def get_required_classes(self) -> List[int]:
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        events = []
        
        current_count = 0
        
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None and getattr(frame_data.detections.boxes, 'id', None) is not None:
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            track_ids = frame_data.detections.boxes.id.cpu().numpy()
            
            for cls_id, track_id in zip(cls_ids, track_ids):
                if int(cls_id) == 0:
                    current_count += 1
                    self.unique_ids.add(int(track_id))
                    
        event = DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PERSON_COUNT",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "current_people_in_frame": current_count,
                "total_unique_people_seen": len(self.unique_ids)
            }
        )
        events.append(event)
                    
        return events
