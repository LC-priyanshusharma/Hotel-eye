import time
import cv2
import numpy as np
from typing import List, Dict, Any
import uuid
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class FireDetectionPlugin(BaseDetectionPlugin):
    """
    Detects fire using OpenCV HSV Thresholding.
    Migrated from legacy EnterpriseSafetyPlugin.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.active_alerts: Dict[str, float] = {}
        logger.info("Initialized FireDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "FireDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # No YOLO classes strictly required for basic fire detection 
        # (could require 0 if we wanted to check person proximity, but we don't right now)
        return []

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        # Fast HSV thresholding check
        blur = cv2.GaussianBlur(frame, (21, 21), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        lower_fire = np.array([15, 150, 200], dtype=np.uint8)
        upper_fire = np.array([35, 255, 255], dtype=np.uint8)
        mask_fire = cv2.inRange(hsv, lower_fire, upper_fire)
        contours, _ = cv2.findContours(mask_fire, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fire_detected = False
        fire_boxes = []
        
        for c in contours:
            if cv2.contourArea(c) > 40000: # Massive fire size only (as per original logic)
                fire_detected = True
                x, y, w, h = cv2.boundingRect(c)
                fire_boxes.append([x, y, x+w, y+h])
                
        # Store state globally for Smoke plugin to read
        tracker_context.get_state(self.plugin_name, camera_id)["fire_detected"] = fire_detected
                
        if fire_detected:
            last_alert = self.active_alerts.get(camera_id, 0)
            if timestamp - last_alert > 3.0: # Debounce 3s
                self.active_alerts[camera_id] = timestamp
                logger.warning(f"🔥 FIRE DETECTED on {camera_id}")
                
            drawings = []
            for (fx1, fy1, fx2, fy2) in fire_boxes:
                drawings.append({
                    "type": "rect",
                    "coords": [fx1, fy1, fx2, fy2],
                    "color": [0, 0, 255],
                    "thickness": 3
                })
                drawings.append({
                    "type": "text",
                    "text": "FIRE",
                    "coords": [fx1, fy1 - 10],
                    "color": [0, 0, 255],
                    "scale": 0.7
                })
                
            drawings.append({
                "type": "text",
                "text": "THREAT: FIRE DETECTED",
                "coords": [50, 160],
                "color": [0, 0, 255],
                "scale": 1.5,
                "thickness": 4
            })
            
            
            # Save Snapshot
            import os
            os.makedirs("snapshots", exist_ok=True)
            filename = f"fire_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            filepath = os.path.join("snapshots", filename)
            cv2.imwrite(filepath, frame)
            
            event = DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="FIRE_DETECTED",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                metadata={
                    "fire_boxes": fire_boxes,
                    "drawings": drawings,
                    "snapshot_file": filename
                }
            )
            events.append(event)
            
        return events
