import time
import cv2
import numpy as np
from typing import List, Dict, Any, Set
import uuid
import os
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
from config.config import config

class AttendanceDetectionPlugin(BaseDetectionPlugin):
    """
    Real OpenCV Appearance-based Re-Identification.
    Migrated from legacy IdentityAnalyticsPlugin.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        # Database of known signatures: ID -> histogram
        self.known_signatures = {} 
        self.next_id = 1
        
        # Authorized database (for features 15, 17)
        # Simulate that ID 1 to 100 are authorized employees for easier testing
        self.authorized_ids = set(range(1, 100))
        
        # Check In / Check Out state
        self.employee_presence: Set[int] = set() 
        self.previous_centroids: Dict[int, tuple] = {} 
        self.recent_logs: List[Dict[str, Any]] = []
        self.last_seen: Dict[int, float] = {}
        
        logger.info("Initialized AttendanceDetectionPlugin")

    @property
    def plugin_name(self) -> str:
        return "AttendanceDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # Person
        return [0]

    def ccw(self, A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def intersect(self, A, B, C, D):
        return self.ccw(A,C,D) != self.ccw(B,C,D) and self.ccw(A,B,C) != self.ccw(A,B,D)

    def extract_signature(self, image_crop):
        hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist.flatten()

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        frame = frame_data.frame
        
        auth_in_frame = []
        unauth_count = 0
        
        # Draw check-in line globally if it exists
        line = config.get_checkin_line_for_camera(camera_id)
        if line:
            # We emit an empty event just to inject the global drawing if line exists
            # so the UI can draw the turnstile line even if no people are present.
            tracker_context.get_state(self.plugin_name, camera_id)["checkin_line_drawn"] = True
            
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None and getattr(frame_data.detections.boxes, 'id', None) is not None:
            boxes = frame_data.detections.boxes.xyxy.cpu().numpy()
            cls_ids = frame_data.detections.boxes.cls.cpu().numpy()
            track_ids = frame_data.detections.boxes.id.cpu().numpy()
            
            for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                if int(cls_id) != 0:
                    continue
                    
                x1, y1, x2, y2 = map(int, box)
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x2 - x1 < 10 or y2 - y1 < 10:
                    continue
                    
                crop = frame[y1:y2, x1:x2]
                sig = self.extract_signature(crop)
                
                # Match against known signatures
                best_match_id = None
                best_score = 0.0
                
                for k_id, k_sig in self.known_signatures.items():
                    score = cv2.compareHist(sig, k_sig, cv2.HISTCMP_CORREL)
                    if score > best_score:
                        best_score = score
                        best_match_id = k_id
                        
                if best_match_id is None or best_score < 0.7:
                    # New person
                    best_match_id = self.next_id
                    self.known_signatures[best_match_id] = sig
                    self.next_id += 1
                else:
                    # Update signature slowly
                    self.known_signatures[best_match_id] = 0.9 * self.known_signatures[best_match_id] + 0.1 * sig
                    
                # Mark as seen
                self.last_seen[best_match_id] = time.time()
                    
                if best_match_id in self.authorized_ids:
                    auth_in_frame.append(f"Employee {best_match_id}")
                    
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    current_centroid = (center_x, center_y)
                    
                    if line and best_match_id in self.previous_centroids:
                        prev_centroid = self.previous_centroids[best_match_id]
                        A, B = line
                        C = prev_centroid
                        D = current_centroid
                        
                        if self.intersect(A, B, C, D):
                            AB_x = B[0] - A[0]
                            AB_y = B[1] - A[1]
                            CD_x = D[0] - C[0]
                            CD_y = D[1] - C[1]
                            cross = AB_x * CD_y - AB_y * CD_x
                            
                            action = None
                            if cross < 0:
                                # Crossed left-to-right (Check In)
                                if best_match_id not in self.employee_presence:
                                    action = "CHECK IN"
                                    self.employee_presence.add(best_match_id)
                                    logger.success(f"✅ Employee {best_match_id} CHECKED IN on {camera_id}")
                            else:
                                # Crossed right-to-left (Check Out)
                                if best_match_id in self.employee_presence:
                                    action = "CHECK OUT"
                                    self.employee_presence.remove(best_match_id)
                                    logger.info(f"🚪 Employee {best_match_id} CHECKED OUT from {camera_id}")
                                    
                            if action:
                                log_entry = {
                                    "employee": f"Emp {best_match_id}", 
                                    "action": action, 
                                    "time": timestamp,
                                    "snapshot_file": None
                                }
                                self.recent_logs.append(log_entry)
                                
                                drawings = []
                                
                                event = DetectionEvent(
                                    plugin_name=self.plugin_name,
                                    event_type=action.replace(" ", "_"),
                                    camera_id=camera_id,
                                    timestamp=timestamp,
                                    confidence=1.0,
                                    metadata={
                                        "employee_id": best_match_id,
                                        "action": action,
                                        "drawings": drawings,
                                        "snapshot_file": None
                                    }
                                )
                                events.append(event)
                                    
                    self.previous_centroids[best_match_id] = current_centroid
                else:
                    unauth_count += 1
                    
        # Evict stale tracking data (Memory Leak Fix)
        # Remove IDs not seen in 5 minutes (300 seconds)
        current_time = time.time()
        stale_ids = [k_id for k_id, last_ts in self.last_seen.items() if current_time - last_ts > 300]
        for stale_id in stale_ids:
            self.known_signatures.pop(stale_id, None)
            self.previous_centroids.pop(stale_id, None)
            self.last_seen.pop(stale_id, None)
            self.employee_presence.discard(stale_id)
            
        self.recent_logs = self.recent_logs[-4:]
        
        # We need a way to continuously supply "attendance_logs" and "authorized_employees" 
        # to the frontend even if no event is currently firing. We can emit a STATE event.
        state_drawings = []
        if line:
            # Draw the check-in line
            state_drawings.append({
                "type": "rect", # API server.py needs to handle line if we want a line, but server.py only has rect and text right now.
                # Fake a line with a thin rect
                "coords": [line[0][0], line[0][1], line[1][0], line[1][1] + 2],
                "color": [255, 0, 0],
                "thickness": -1
            })
            
        state_event = DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="ATTENDANCE_STATE",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "authorized_employees_in_frame": list(set(auth_in_frame)),
                "unauthorized_count": unauth_count,
                "attendance_logs": self.recent_logs,
                "drawings": state_drawings
            }
        )
        events.append(state_event)
                    
        return events
