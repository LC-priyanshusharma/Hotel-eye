import time
import cv2
import numpy as np
from typing import List
import uuid
from loguru import logger
import os

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class PPEDetectionPlugin(BaseDetectionPlugin):
    """
    Plugin for checking PPE compliance (Hard hats, Safety vests).
    Uses YOLO class 0 (Person) and performs HSV color thresholding within the bounding box
    to look for high-visibility safety colors (yellow, orange, bright green).
    If safety colors are missing, it assumes PPE is missing.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.last_alert_time = {}
        # Colors to search for in HSV format (Yellow, Orange, Bright Green)
        # Note: These are rough approximations for high-visibility gear.
        self.lower_color1 = np.array([10, 100, 100], dtype=np.uint8) # Orange/Yellow
        self.upper_color1 = np.array([40, 255, 255], dtype=np.uint8)
        
        self.lower_color2 = np.array([40, 50, 100], dtype=np.uint8) # Bright Green
        self.upper_color2 = np.array([80, 255, 255], dtype=np.uint8)
        
        logger.info("Initialized PPEDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "PPEDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        return [0]  # Requires Person class

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        detections = frame_data.detections

        if not hasattr(detections, 'boxes') or detections.boxes is None:
            return events

        # Debounce alerts per camera (1 alert every 5 seconds)
        last_time = self.last_alert_time.get(camera_id, 0)
        if timestamp - last_time < 5.0:
            return events

        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        persons_without_ppe = []
        drawings = []

        for box in detections.boxes:
            cls_id = int(box.cls[0].item())
            if cls_id != 0:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
            # Ensure coordinates are within frame bounds
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue

            # Extract the person region
            person_roi = hsv_frame[y1:y2, x1:x2]
            
            # Create masks for safety colors
            mask1 = cv2.inRange(person_roi, self.lower_color1, self.upper_color1)
            mask2 = cv2.inRange(person_roi, self.lower_color2, self.upper_color2)
            combined_mask = cv2.bitwise_or(mask1, mask2)
            
            # Calculate percentage of safety color
            safety_pixels = cv2.countNonZero(combined_mask)
            total_pixels = (x2 - x1) * (y2 - y1)
            safety_ratio = safety_pixels / float(total_pixels) if total_pixels > 0 else 0
            
            # If less than 2% of the person's bounding box has safety colors, assume NO PPE
            if safety_ratio < 0.02:
                persons_without_ppe.append([x1, y1, x2, y2])
                drawings.append({
                    "type": "rect",
                    "coords": [x1, y1, x2, y2],
                    "color": [0, 0, 255], # Red box for missing PPE
                    "thickness": 2
                })
                drawings.append({
                    "type": "text",
                    "text": "NO PPE",
                    "coords": [x1, y1 - 5],
                    "color": [0, 0, 255],
                    "scale": 0.6
                })

        if persons_without_ppe:
            self.last_alert_time[camera_id] = timestamp
            logger.warning(f"⚠️ Missing PPE Detected on {camera_id}! Count: {len(persons_without_ppe)}")
            
            # Save Snapshot
            os.makedirs("snapshots", exist_ok=True)
            filename = f"ppe_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
            filepath = os.path.join("snapshots", filename)
            
            # Draw on a copy of the frame to save
            snapshot_frame = frame.copy()
            for (px1, py1, px2, py2) in persons_without_ppe:
                cv2.rectangle(snapshot_frame, (px1, py1), (px2, py2), (0, 0, 255), 2)
                cv2.putText(snapshot_frame, "NO PPE", (px1, py1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
            cv2.imwrite(filepath, snapshot_frame)

            event = DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="PPE_MISSING",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                metadata={
                    "persons_without_ppe": persons_without_ppe,
                    "drawings": drawings,
                    "snapshot_file": filename
                }
            )
            events.append(event)

        return events
