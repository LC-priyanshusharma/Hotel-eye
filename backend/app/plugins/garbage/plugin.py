from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, DetectionEvent, FrameData, TrackerContext
from app.plugins.garbage.config import garbage_config
from app.plugins.garbage.constants import GARBAGE_CLASS_IDS
from app.plugins.garbage.service import GarbageDetectionService

class GarbageDetectionPlugin(BaseDetectionPlugin):
    """
    Plugin for detecting and alerting on stationary garbage.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.service = GarbageDetectionService()
        logger.info(f"Initialized GarbageDetectionPlugin (Threshold: {garbage_config.GARBAGE_DWELL_TIME_SECONDS}s)")
        
    @property
    def plugin_name(self) -> str:
        return "GarbageDetectionPlugin"
        
    def get_required_classes(self) -> List[int]:
        return GARBAGE_CLASS_IDS
        
    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        # Filter detections for garbage classes only
        if frame_data.detections is None or frame_data.detections.boxes is None or frame_data.detections.boxes.id is None:
            return []
            
        boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
        cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
        confs = frame_data.detections.boxes.conf.cpu().numpy()
        track_ids = frame_data.detections.boxes.id.cpu().numpy()
        
        # Filter
        valid_indices = [i for i, cls in enumerate(cls_ids) if int(cls) in self.get_required_classes() and confs[i] >= garbage_config.GARBAGE_CONFIDENCE_THRESHOLD]
        
        if not valid_indices:
            return []
            
        f_boxes = boxes[valid_indices]
        f_cls = cls_ids[valid_indices]
        f_confs = confs[valid_indices]
        f_tracks = track_ids[valid_indices]
        
        return self.service.validate_and_track(
            camera_id=frame_data.camera_id,
            boxes=f_boxes,
            cls_ids=(f_cls, f_confs),
            track_ids=f_tracks,
            frame=frame_data.frame,
            timestamp=frame_data.timestamp,
            tracker_context=tracker_context
        )
