import cv2
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class TamperDetectionPlugin(BaseDetectionPlugin):
    """
    Detects Camera Tampering (Lens Covered or Camera Shifted) using OpenCV.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.camera_backgrounds: Dict[str, np.ndarray] = {}
        logger.info("Initialized TamperDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "TamperDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        return []

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        events = []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        mean_brightness = np.mean(gray)
        is_covered = float(mean_brightness) < 10.0
        
        is_shifted = False
        
        small_gray = cv2.resize(gray, (320, 240))
        
        if camera_id not in self.camera_backgrounds:
            self.camera_backgrounds[camera_id] = small_gray.astype(float)
        else:
            bg = self.camera_backgrounds[camera_id]
            diff = cv2.absdiff(bg.astype(np.uint8), small_gray)
            mean_diff = np.mean(diff)
            
            if mean_diff > 50.0:
                is_shifted = True
                
            cv2.accumulateWeighted(small_gray, bg, 0.05)
            self.camera_backgrounds[camera_id] = bg
            
        tamper_alert = is_covered or is_shifted
        
        if tamper_alert:
            # We don't want to draw on the screen because the camera is dead/shifted,
            # but we will send an alert
            logger.warning(f"⚠️ CAMERA TAMPERING on {camera_id}")
            
        event = DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="TAMPER_DETECTED" if tamper_alert else "TAMPER_OK",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "tamper_alert": tamper_alert,
                "is_covered": is_covered,
                "is_shifted": is_shifted,
                "brightness": round(float(mean_brightness), 2)
            }
        )
        events.append(event)
            
        return events
