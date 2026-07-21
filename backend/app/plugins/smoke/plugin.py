import time
import cv2
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class SmokeDetectionPlugin(BaseDetectionPlugin):
    """
    Detects smoke using OpenCV Background Subtraction and HSV Thresholding.
    Migrated from legacy EnterpriseSafetyPlugin.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # Background subtractor for smoke - very sensitive for faint smoke
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=5, detectShadows=False)
        self.active_alerts: Dict[str, float] = {}
        logger.info("Initialized SmokeDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "SmokeDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # Requires Person class (0) to avoid false positives on cigarette smoke
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        # 1. Downscale for performance
        small = cv2.resize(frame, (320, 240))
        scale_x = frame.shape[1] / 320.0
        scale_y = frame.shape[0] / 240.0
        
        fg_mask = self.bg_subtractor.apply(small)
        _, fg_thresh = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)
        contours_smoke, _ = cv2.findContours(fg_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 2. Collect person bounding boxes in small scale
        person_boxes_small = []
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None:
            boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) == 0: # Person
                    x1, y1, x2, y2 = box
                    sx1, sy1 = int(x1 / scale_x), int(y1 / scale_y)
                    sx2, sy2 = int(x2 / scale_x), int(y2 / scale_y)
                    person_boxes_small.append((sx1, sy1, sx2, sy2))
                    
        smoke_detected = False
        smoke_boxes = []
        
        for c in contours_smoke:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)
            bx1, by1 = int(x * scale_x), int(y * scale_y)
            bx2, by2 = int((x+w) * scale_x), int((y+h) * scale_y)
            
            is_massive_smoke = area > 20000
            if is_massive_smoke:
                extent = area / float(w * h)
                if extent > 0.7:
                    is_massive_smoke = False
                    
            is_cigarette_smoke = False
            if 20 < area < 3000:
                cx, cy, cw, ch = cv2.boundingRect(c)
                extent = area / float(cw * ch)
                if extent < 0.65:
                    if not person_boxes_small:
                        is_cigarette_smoke = True
                    else:
                        for (px1, py1, px2, py2) in person_boxes_small:
                            ph = py2 - py1
                            head_bottom_y = py1 + int(ph * 0.3)
                            if (px1 - 20 < cx < px2 + 20) and (py1 - 20 < cy < head_bottom_y):
                                is_cigarette_smoke = True
                                break
                                
            if is_massive_smoke or is_cigarette_smoke:
                crop = small[y:y+h, x:x+w]
                if crop.size == 0: continue
                
                hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                s_channel = hsv_crop[:,:,1]
                v_channel = hsv_crop[:,:,2]
                
                if not person_boxes_small:
                    if np.mean(s_channel) < 40 and np.mean(v_channel) > 130:
                        smoke_detected = True
                        smoke_boxes.append((bx1, by1, bx2, by2))
                        break
                else:
                    if np.mean(s_channel) < 30 and np.mean(v_channel) > 140: 
                        smoke_detected = True
                        smoke_boxes.append((bx1, by1, bx2, by2))
                        break
                        
        if smoke_detected:
            # Check if fire is also present (business requirement for smoke)
            # This relies on FireDetectionPlugin running before SmokeDetectionPlugin
            fire_state = tracker_context.get_state("FireDetectionPlugin", camera_id)
            if not fire_state.get("fire_detected", False):
                smoke_detected = False
                
        # Debounce alerts (don't spam every frame)
        if smoke_detected:
            last_alert = self.active_alerts.get(camera_id, 0)
            if timestamp - last_alert > 3.0: # New alert if 3 seconds passed
                self.active_alerts[camera_id] = timestamp
                logger.warning(f"🚨 SMOKE DETECTED on {camera_id}")
                
            # Create declarative drawing instructions for the UI
            drawings = []
            for (sx1, sy1, sx2, sy2) in smoke_boxes:
                drawings.append({
                    "type": "rect",
                    "coords": [sx1, sy1, sx2, sy2],
                    "color": [200, 200, 200],
                    "thickness": 2
                })
                drawings.append({
                    "type": "text",
                    "text": "SMOKE",
                    "coords": [sx1, sy1 - 10],
                    "color": [200, 200, 200],
                    "scale": 0.7
                })
            
            drawings.append({
                "type": "text",
                "text": "THREAT: SMOKE DETECTED",
                "coords": [50, 100],
                "color": [0, 0, 255],
                "scale": 1.5,
                "thickness": 4
            })
            
            event = DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="SMOKE_DETECTED",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                metadata={
                    "smoke_boxes": smoke_boxes,
                    "drawings": drawings
                }
            )
            events.append(event)
            
        return events
