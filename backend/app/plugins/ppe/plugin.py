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
    Plugin for checking PPE compliance and categorizing by contractor.
    Contractor 1: Blue PPE
    Contractor 2: Yellow/Orange PPE
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.last_alert_time = {}
        
        # Yellow/Orange (Contractor 2)
        self.lower_yellow = np.array([10, 100, 100], dtype=np.uint8)
        self.upper_yellow = np.array([40, 255, 255], dtype=np.uint8)
        
        # Blue (Contractor 1)
        # OpenCV HSV for blue is around H=100-130
        self.lower_blue = np.array([100, 150, 0], dtype=np.uint8)
        self.upper_blue = np.array([140, 255, 255], dtype=np.uint8)
        
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

        if not detections:
            return events

        contractor_1_count = 0  # Blue
        contractor_2_count = 0  # Yellow
        missing_ppe_count = 0

        if frame is None:
            for det in detections:
                if det.class_id == 0:
                    contractor_1_count += 1
            events.append(DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="PPE_STATS",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                metadata={
                    "contractor_1_count": contractor_1_count,
                    "contractor_2_count": contractor_2_count,
                    "missing_ppe_count": missing_ppe_count,
                    "drawings": []
                }
            ))
            return events

        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        persons_without_ppe = []
        drawings = []

        for det in detections:
            cls_id = det.class_id
            if cls_id != 0:
                continue

            x1, y1, x2, y2 = map(int, det.bbox)
            
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue

            person_roi = hsv_frame[y1:y2, x1:x2]
            
            # Masks
            mask_yellow = cv2.inRange(person_roi, self.lower_yellow, self.upper_yellow)
            mask_blue = cv2.inRange(person_roi, self.lower_blue, self.upper_blue)
            
            pixels_yellow = cv2.countNonZero(mask_yellow)
            pixels_blue = cv2.countNonZero(mask_blue)
            
            total_pixels = (x2 - x1) * (y2 - y1)
            ratio_yellow = pixels_yellow / float(total_pixels) if total_pixels > 0 else 0
            ratio_blue = pixels_blue / float(total_pixels) if total_pixels > 0 else 0
            
            THRESHOLD = 0.02
            
            is_contractor_1 = ratio_blue >= THRESHOLD
            is_contractor_2 = ratio_yellow >= THRESHOLD
            
            if is_contractor_1 and is_contractor_2:
                # If both colors are present, pick the one with more pixels
                if ratio_blue > ratio_yellow:
                    is_contractor_2 = False
                else:
                    is_contractor_1 = False

            if is_contractor_1:
                contractor_1_count += 1
                drawings.append({
                    "type": "rect", "coords": [x1, y1, x2, y2], "color": [255, 0, 0], "thickness": 2
                })
                drawings.append({
                    "type": "text", "text": "Contractor 1", "coords": [x1, y1 - 5], "color": [255, 0, 0], "scale": 0.6
                })
            elif is_contractor_2:
                contractor_2_count += 1
                drawings.append({
                    "type": "rect", "coords": [x1, y1, x2, y2], "color": [0, 255, 255], "thickness": 2
                })
                drawings.append({
                    "type": "text", "text": "Contractor 2", "coords": [x1, y1 - 5], "color": [0, 255, 255], "scale": 0.6
                })
            else:
                missing_ppe_count += 1
                persons_without_ppe.append([x1, y1, x2, y2])
                drawings.append({
                    "type": "rect", "coords": [x1, y1, x2, y2], "color": [0, 0, 255], "thickness": 2
                })
                drawings.append({
                    "type": "text", "text": "NO PPE", "coords": [x1, y1 - 5], "color": [0, 0, 255], "scale": 0.6
                })

        # Emit Real-time Stats for Dashboard
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PPE_STATS",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "contractor_1_count": contractor_1_count,
                "contractor_2_count": contractor_2_count,
                "missing_ppe_count": missing_ppe_count,
                "drawings": drawings
            }
        ))

        # Debounced Alert for Missing PPE (every 5 seconds)
        last_time = self.last_alert_time.get(camera_id, 0)
        if persons_without_ppe and (timestamp - last_time >= 5.0):
            self.last_alert_time[camera_id] = timestamp
            logger.warning(f"⚠️ Missing PPE Detected on {camera_id}! Count: {len(persons_without_ppe)}")
            
            snapshot_path = None
            try:
                # Crop the first person without PPE
                px1, py1, px2, py2 = persons_without_ppe[0]
                h, w = frame.shape[:2]
                pad_x = int((px2 - px1) * 0.2)
                pad_y = int((py2 - py1) * 0.2)
                cx1, cy1 = max(0, int(px1 - pad_x)), max(0, int(py1 - pad_y))
                cx2, cy2 = min(w, int(px2 + pad_x)), min(h, int(py2 + pad_y))
                
                if cx2 - cx1 > 10 and cy2 - cy1 > 10:
                    crop = frame[cy1:cy2, cx1:cx2].copy()
                    os.makedirs("snapshots/ppe", exist_ok=True)
                    snapshot_filename = f"snapshots/ppe/ppe_{uuid.uuid4().hex[:8]}.jpg"
                    cv2.imwrite(snapshot_filename, crop)
                    snapshot_path = snapshot_filename
            except Exception as e:
                logger.error(f"Failed to save PPE snapshot: {e}")
            
            events.append(DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="PPE_MISSING",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                metadata={
                    "persons_without_ppe": persons_without_ppe,
                    "drawings": drawings,
                    "snapshot_file": snapshot_path
                }
            ))

        return events
