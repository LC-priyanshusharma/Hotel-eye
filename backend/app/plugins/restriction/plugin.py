from typing import List
from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
import time
import cv2
import numpy as np

class RestrictionZonePlugin(BaseDetectionPlugin):
    """
    Detects if a person enters a predefined restricted polygonal zone.
    Emits a RESTRICTION_ALERT event if the bottom center of the person's bounding box is inside.
    """
    
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # Define a polygon for the restricted zone. 
        self.zone_pts = [[300, 200], [800, 200], [900, 600], [200, 600]]
        self.zone_poly = np.array(self.zone_pts, np.int32)
        
        self.last_alert_time = 0
        self.alert_cooldown = 5.0

    @property
    def plugin_name(self) -> str:
        return "RestrictionZonePlugin"

    def get_required_classes(self) -> List[int]:
        # COCO class 0 is person
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        is_intruder = False
        
        # Draw the zone
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="RESTRICTION_ZONE_DRAW",
            camera_id=frame_data.camera_id,
            timestamp=frame_data.timestamp,
            confidence=1.0,
            metadata={
                "drawings": [
                    {
                        "type": "poly",
                        "coords": self.zone_pts,
                        "color": [0, 0, 255], # BGR (Red)
                        "thickness": 2,
                        "opacity": 0.35
                    },
                    {
                        "type": "text",
                        "text": "RESTRICTED ZONE",
                        "coords": [self.zone_pts[0][0], max(0, self.zone_pts[0][1] - 10)],
                        "color": [0, 0, 255],
                        "scale": 0.7,
                        "thickness": 2
                    }
                ]
            }
        ))
        
        for det in frame_data.detections:
            cls_id = det.class_id
            conf = det.confidence
            
            if cls_id == 0 and conf > 0.4:
                x1, y1, x2, y2 = det.bbox
                
                cx = int((x1 + x2) / 2)
                cy = int(y2)
                
                dist = cv2.pointPolygonTest(self.zone_poly, (cx, cy), False)
                if dist >= 0:
                    is_intruder = True
                    
                    # Draw a warning box around the intruder
                    events.append(DetectionEvent(
                        plugin_name=self.plugin_name,
                        event_type="RESTRICTION_INTRUDER_TRACK",
                        camera_id=frame_data.camera_id,
                        timestamp=frame_data.timestamp,
                        confidence=conf,
                        metadata={
                            "drawings": [
                                {
                                    "type": "rect",
                                    "coords": [x1, y1, x2, y2],
                                    "color": [0, 0, 255],
                                    "thickness": 3
                                },
                                {
                                    "type": "text",
                                    "text": "INTRUDER",
                                    "coords": [x1, max(0, y1 - 10)],
                                    "color": [0, 0, 255],
                                    "scale": 0.8,
                                    "thickness": 2
                                }
                            ]
                        }
                    ))
                    break
                        
        if is_intruder:
            now = time.time()
            if now - self.last_alert_time > self.alert_cooldown:
                self.last_alert_time = now
                events.append(DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type="RESTRICTION_ALERT",
                    camera_id=frame_data.camera_id,
                    timestamp=frame_data.timestamp,
                    confidence=1.0,
                    metadata={
                        "severity": "critical",
                        "description": f"Intrusion detected in restricted zone on {frame_data.camera_id}!"
                    }
                ))
                
        return events
