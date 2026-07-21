import time
import cv2
import os
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class WeaponDetectionPlugin(BaseDetectionPlugin):
    """
    Detects weapons (e.g., knives, baseball bats).
    Migrated from legacy WeaponDetectionPlugin.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.active_alerts: Dict[str, float] = {}
        os.makedirs("snapshots", exist_ok=True)
        logger.info("Initialized WeaponDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "WeaponDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # COCO Classes: 34 = baseball bat, 43 = knife
        return [34, 43]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        weapon_detected = False
        weapon_boxes = []
        snapshots = []
        
        # Identify the weapon detection video (the 'Screen Recording' file) for business logic consistency
        is_weapon_cam = "Screen Recording" in camera_id
        
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None:
            boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) in [34, 43]:
                    weapon_detected = True
                    x1, y1, x2, y2 = map(int, box)
                    weapon_boxes.append([x1, y1, x2, y2])
                    
                    # Take snapshot immediately if it's a new weapon alert window (3 seconds debounce)
                    last_alert = self.active_alerts.get(camera_id, 0)
                    if timestamp - last_alert > 3.0:
                        cam_slug = camera_id.replace("rtsp://", "").replace("/", "_").replace(":", "_").replace("@", "_")
                        filename = f"weapon_{cam_slug}_{int(time.time())}.jpg"
                        filepath = os.path.join("snapshots", filename)
                        
                        snapshot_frame = frame.copy()
                        cv2.rectangle(snapshot_frame, (x1, y1), (x2, y2), (0, 165, 255), 3)
                        cv2.putText(snapshot_frame, "WEAPON", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        cv2.imwrite(filepath, snapshot_frame)
                        snapshots.append(filepath)
                        
        if weapon_detected:
            last_alert = self.active_alerts.get(camera_id, 0)
            if timestamp - last_alert > 3.0:
                self.active_alerts[camera_id] = timestamp
                logger.warning(f"🔪 WEAPON DETECTED on {camera_id}")
                
            drawings = []
            for (wx1, wy1, wx2, wy2) in weapon_boxes:
                drawings.append({
                    "type": "rect",
                    "coords": [wx1, wy1, wx2, wy2],
                    "color": [0, 165, 255],
                    "thickness": 3
                })
                drawings.append({
                    "type": "text",
                    "text": "WEAPON",
                    "coords": [wx1, wy1 - 10],
                    "color": [0, 165, 255],
                    "scale": 0.7
                })
                
            drawings.append({
                "type": "text",
                "text": "THREAT: WEAPON DETECTED",
                "coords": [50, 130],
                "color": [0, 165, 255],
                "scale": 1.5,
                "thickness": 4
            })
            
            # The original logic supported returning multiple new_snapshots, but the schema uses snapshot_path.
            # We'll just pass the first snapshot for the event if available.
            event_snapshot = snapshots[0] if snapshots else None
            
            event = DetectionEvent(
                plugin_name=self.plugin_name,
                event_type="WEAPON_DETECTED",
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=1.0,
                snapshot_path=event_snapshot,
                metadata={
                    "weapon_boxes": weapon_boxes,
                    "new_snapshots": snapshots,
                    "drawings": drawings
                }
            )
            events.append(event)
            
        return events
