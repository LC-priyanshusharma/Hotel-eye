import time
import cv2
import os
import numpy as np
from typing import List, Dict, Any, Set
from shapely.geometry import Point, Polygon
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class IntrusionDetectionPlugin(BaseDetectionPlugin):
    """
    Handles Intrusion Detection, Restricted Zones, and Loitering Detection.
    Migrated from legacy SpatialAnalyticsPlugin.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # Maps camera_id -> { track_id: first_seen_timestamp }
        self.loitering_memory: Dict[str, Dict[int, float]] = {}
        # Maps camera_id -> set of track_ids that have already been snapped
        self.known_intrusions: Dict[str, Set[int]] = {}
        os.makedirs("snapshots", exist_ok=True)
        logger.info("Initialized IntrusionDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "IntrusionDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # Person
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        if camera_id not in self.loitering_memory:
            self.loitering_memory[camera_id] = {}
        if camera_id not in self.known_intrusions:
            self.known_intrusions[camera_id] = set()
            
        zone_coords = self.config.get_zone_for_camera(camera_id) if self.config else []
        if not zone_coords:
            return events
            
        zone_poly = Polygon(zone_coords)
        
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
                
                if zone_poly.contains(feet_point):
                    # Intrusion Detected
                    if track_id not in self.known_intrusions[camera_id]:
                        self.known_intrusions[camera_id].add(track_id)
                        

                        
                        drawings = []
                        drawings.append({
                            "type": "rect",
                            "coords": [int(x1), int(y1), int(x2), int(y2)],
                            "color": [0, 0, 255],
                            "thickness": 3
                        })
                        drawings.append({
                            "type": "text",
                            "text": "INTRUDER",
                            "coords": [int(x1), int(y1) - 10],
                            "color": [0, 0, 255],
                            "scale": 0.7
                        })
                        
                        event = DetectionEvent(
                            plugin_name=self.plugin_name,
                            event_type="INTRUSION_DETECTED",
                            camera_id=camera_id,
                            timestamp=timestamp,
                            confidence=1.0,
                            snapshot_path=None,
                            metadata={
                                "track_id": track_id,
                                "zone": zone_coords,
                                "drawings": drawings
                            }
                        )
                        events.append(event)
                        logger.warning(f"🚨 INTRUSION DETECTED: Track {track_id} on {camera_id}")
                    
                    # Loitering logic
                    if track_id not in self.loitering_memory[camera_id]:
                        self.loitering_memory[camera_id][track_id] = timestamp
                    else:
                        time_spent = timestamp - self.loitering_memory[camera_id][track_id]
                        if time_spent >= (self.config.LOITERING_THRESHOLD_SECONDS if self.config else 60):
                            # Debounce loitering alerts (send once per configured threshold)
                            # To do this simply, we can reset the timer when an alert is fired
                            self.loitering_memory[camera_id][track_id] = timestamp
                            
                            drawings = []
                            drawings.append({
                                "type": "rect",
                                "coords": [int(x1), int(y1), int(x2), int(y2)],
                                "color": [0, 165, 255], # Orange for loitering
                                "thickness": 3
                            })
                            drawings.append({
                                "type": "text",
                                "text": f"LOITERING ({int(time_spent)}s)",
                                "coords": [int(x1), int(y1) - 10],
                                "color": [0, 165, 255],
                                "scale": 0.7
                            })
                            
                            levent = DetectionEvent(
                                plugin_name=self.plugin_name,
                                event_type="LOITERING_DETECTED",
                                camera_id=camera_id,
                                timestamp=timestamp,
                                confidence=1.0,
                                metadata={
                                    "track_id": track_id,
                                    "time_spent": time_spent,
                                    "drawings": drawings
                                }
                            )
                            events.append(levent)
                            logger.warning(f"⚠️ LOITERING DETECTED: Track {track_id} on {camera_id} for {int(time_spent)}s")
                else:
                    if track_id in self.loitering_memory[camera_id]:
                        del self.loitering_memory[camera_id][track_id]
                        
        # Cleanup
        memory = self.loitering_memory[camera_id]
        to_delete = [tid for tid in memory.keys() if tid not in current_frame_ids]
        for tid in to_delete:
            del memory[tid]
            
        intrusions_memory = self.known_intrusions[camera_id]
        to_delete_intrusions = [tid for tid in intrusions_memory if tid not in current_frame_ids]
        for tid in to_delete_intrusions:
            intrusions_memory.remove(tid)
            
        # Draw the zone polygon globally if there's any active zone
        # We can add a generic UI drawing for the zone that is always active
        if events:
            # Flatten zone coordinates for drawing
            pts = np.array(zone_coords, np.int32).reshape((-1, 1, 2))
            
            # Since the backend doesn't support 'poly' drawing type natively yet in server.py,
            # we'd need to either update server.py to draw polygons, or just draw lines.
            # Let's add poly support to server.py later, but for now we'll supply poly metadata.
            # Adding poly metadata to the first event
            events[0].metadata.setdefault("drawings", []).append({
                "type": "poly",
                "coords": zone_coords,
                "color": [255, 0, 0],
                "thickness": 2
            })
            
        return events
