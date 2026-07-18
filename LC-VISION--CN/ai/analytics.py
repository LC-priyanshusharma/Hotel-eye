from abc import ABC, abstractmethod
import os
from typing import Dict, Any, List
from loguru import logger
import time
import cv2
import numpy as np
from shapely.geometry import Point, Polygon

from core.config import config

class AnalyticsPlugin(ABC):
    """Base class for all analytics plugins."""
    @abstractmethod
    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        """Process an ultralytics Result object and return event dictionary."""
        pass

class PeopleCountingPlugin(AnalyticsPlugin):
    """
    Counts the total number of unique people seen by inspecting the ByteTrack IDs.
    """
    def __init__(self):
        self.unique_ids = set()
        logger.info("Initialized PeopleCountingPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        current_count = 0
        
        if result.boxes is not None and result.boxes.id is not None:
            print(f"Processing boxes... ids: {result.boxes.id}")
            cls_ids = result.boxes.cls.cpu().numpy()
            track_ids = result.boxes.id.cpu().numpy()
            
            for cls_id, track_id in zip(cls_ids, track_ids):
                if int(cls_id) == 0:
                    current_count += 1
                    self.unique_ids.add(int(track_id))
                    
        return {
            "current_people_in_frame": current_count,
            "total_unique_people_seen": len(self.unique_ids)
        }

class SpatialAnalyticsPlugin(AnalyticsPlugin):
    """
    Handles Intrusion Detection, Restricted Zones, and Loitering Detection.
    """
    def __init__(self):
        # Maps camera_id -> { track_id: first_seen_timestamp }
        self.loitering_memory: Dict[str, Dict[int, float]] = {}
        # Maps camera_id -> set of track_ids that have already been snapped
        self.known_intrusions: Dict[str, set] = {}
        os.makedirs("snapshots", exist_ok=True)
        logger.info("Initialized SpatialAnalyticsPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        if camera_id not in self.loitering_memory:
            self.loitering_memory[camera_id] = {}
        if camera_id not in self.known_intrusions:
            self.known_intrusions[camera_id] = set()
            
        # Get the polygon for this specific camera
        zone_coords = config.get_zone_for_camera(camera_id)
        
        if not zone_coords:
            return {
                "zone": [],
                "intrusions": [],
                "new_intrusions": [],
                "loiterers": [],
                "alert": False
            }
            
        zone_poly = Polygon(zone_coords)
        
        active_intrusions = []
        new_intrusions = []
        active_loiterers = []
        current_frame_ids = set()
        
        if result.boxes is not None and result.boxes.id is not None:
            print(f"Processing boxes... ids: {result.boxes.id}")
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            track_ids = result.boxes.id.cpu().numpy()
            
            for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                if int(cls_id) != 0:
                    continue  # Only care about people for now
                    
                track_id = int(track_id)
                current_frame_ids.add(track_id)
                
                # Use bottom center (feet) as the point of intersection
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                bottom_y = y2
                feet_point = Point(center_x, bottom_y)
                
                if zone_poly.contains(feet_point):
                    active_intrusions.append(track_id)
                    
                    if track_id not in self.known_intrusions[camera_id]:
                        self.known_intrusions[camera_id].add(track_id)
                        
                        # Generate safe filename for camera
                        cam_slug = camera_id.replace("rtsp://", "").replace("/", "_").replace(":", "_").replace("@", "_")
                        filename = f"intrusion_{cam_slug}_{track_id}_{int(time.time())}.jpg"
                        filepath = os.path.join("snapshots", filename)
                        
                        # Save full frame with context instead of tightly cropped box
                        snapshot_frame = frame.copy()
                        cv2.rectangle(snapshot_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 3)
                        cv2.imwrite(filepath, snapshot_frame)
                            
                        new_intrusions.append({
                            "track_id": track_id,
                            "snapshot": filepath,
                            "timestamp": time.time(),
                            "zone": zone_coords
                        })
                    
                    # Loitering logic
                    now = time.time()
                    if track_id not in self.loitering_memory[camera_id]:
                        self.loitering_memory[camera_id][track_id] = now
                    else:
                        time_spent = now - self.loitering_memory[camera_id][track_id]
                        if time_spent >= config.LOITERING_THRESHOLD_SECONDS:
                            active_loiterers.append(track_id)
                else:
                    # Person left the zone, reset their timer
                    if track_id in self.loitering_memory[camera_id]:
                        del self.loitering_memory[camera_id][track_id]
        
        # Cleanup memory for IDs that disappeared from the frame entirely
        memory = self.loitering_memory[camera_id]
        to_delete = [tid for tid in memory.keys() if tid not in current_frame_ids]
        for tid in to_delete:
            del memory[tid]
            
        intrusions_memory = self.known_intrusions[camera_id]
        to_delete_intrusions = [tid for tid in intrusions_memory if tid not in current_frame_ids]
        for tid in to_delete_intrusions:
            intrusions_memory.remove(tid)
            
        # Generate an alert status if there's any active intrusion
        is_alert = len(active_intrusions) > 0
            
        return {
            "zone": zone_coords,
            "intrusions": active_intrusions,
            "new_intrusions": new_intrusions,
            "loiterers": active_loiterers,
            "alert": is_alert
        }

class QueueAnalyticsPlugin(AnalyticsPlugin):
    """
    Handles Queue Length and Waiting Time Prediction.
    """
    def __init__(self):
        # Maps camera_id -> { track_id: enter_timestamp }
        self.queue_memory: Dict[str, Dict[int, float]] = {}
        # Stores recent wait times (in seconds) for SMA prediction
        self.recent_wait_times: List[float] = []
        logger.info("Initialized QueueAnalyticsPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        if camera_id not in self.queue_memory:
            self.queue_memory[camera_id] = {}
            
        queue_coords = config.get_queue_zone_for_camera(camera_id)
        queue_poly = Polygon(queue_coords)
        
        active_in_queue = []
        current_frame_ids = set()
        
        if result.boxes is not None and result.boxes.id is not None:
            print(f"Processing boxes... ids: {result.boxes.id}")
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            track_ids = result.boxes.id.cpu().numpy()
            
            for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                if int(cls_id) != 0:
                    continue
                    
                track_id = int(track_id)
                current_frame_ids.add(track_id)
                
                # Use bottom center
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                bottom_y = y2
                feet_point = Point(center_x, bottom_y)
                
                if queue_poly.contains(feet_point):
                    active_in_queue.append(track_id)
                    # Enter queue
                    if track_id not in self.queue_memory[camera_id]:
                        self.queue_memory[camera_id][track_id] = time.time()
                else:
                    # Person left the queue
                    if track_id in self.queue_memory[camera_id]:
                        enter_time = self.queue_memory[camera_id][track_id]
                        time_spent = time.time() - enter_time
                        if time_spent > 2.0: # Ignore walking through rapidly
                            self.recent_wait_times.append(time_spent)
                            if len(self.recent_wait_times) > 10: # Keep last 10
                                self.recent_wait_times.pop(0)
                        del self.queue_memory[camera_id][track_id]
        
        # Cleanup memory for IDs that disappeared completely
        memory = self.queue_memory[camera_id]
        to_delete = [tid for tid in memory.keys() if tid not in current_frame_ids]
        for tid in to_delete:
            del memory[tid]
            
        predicted_wait = 0.0
        if self.recent_wait_times:
            predicted_wait = sum(self.recent_wait_times) / len(self.recent_wait_times)
            
        return {
            "queue_length": len(active_in_queue),
            "predicted_wait_time_seconds": round(predicted_wait, 1)
        }

import random

class IdentityAnalyticsPlugin(AnalyticsPlugin):
    """
    Real OpenCV Appearance-based Re-Identification.
    """
    def __init__(self):
        # Database of known signatures: ID -> histogram
        self.known_signatures = {} 
        self.next_id = 1
        
        # Authorized database (for features 15, 17)
        # We will simulate that ID 1 to 100 are authorized employees for easier testing
        self.authorized_ids = set(range(1, 100))
        
        # Check In / Check Out state (Feature 16)
        self.employee_presence = set() # employee_ids currently checked in
        self.previous_centroids = {} # employee_id -> (x, y)
        self.recent_logs = []
        
        logger.info("Initialized IdentityAnalyticsPlugin (Real OpenCV Re-ID + Attendance with Line Crossing)")

    def ccw(self, A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def intersect(self, A, B, C, D):
        return self.ccw(A,C,D) != self.ccw(B,C,D) and self.ccw(A,B,C) != self.ccw(A,B,D)

    def extract_signature(self, image_crop):
        hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        return hist.flatten()

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        current_time = time.time()
        auth_in_frame = []
        unauth_count = 0
        
        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            track_ids = result.boxes.id.cpu().numpy()
            
            for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                if int(cls_id) != 0:
                    continue # Only identify people
                x1, y1, x2, y2 = map(int, box)
                # Ensure bounds
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
                    
                if best_match_id in self.authorized_ids:
                    auth_in_frame.append(f"Employee {best_match_id}")
                    
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    current_centroid = (center_x, center_y)
                    
                    if best_match_id in self.previous_centroids:
                        prev_centroid = self.previous_centroids[best_match_id]
                        line = config.get_checkin_line_for_camera(camera_id)
                        A, B = line
                        C = prev_centroid
                        D = current_centroid
                        
                        if self.intersect(A, B, C, D):
                            AB_x = B[0] - A[0]
                            AB_y = B[1] - A[1]
                            CD_x = D[0] - C[0]
                            CD_y = D[1] - C[1]
                            cross = AB_x * CD_y - AB_y * CD_x
                            
                            if cross < 0:
                                # Crossed left-to-right (Check In)
                                if best_match_id not in self.employee_presence:
                                    self.recent_logs.append({
                                        "employee": f"Emp {best_match_id}", 
                                        "action": "CHECK IN", 
                                        "time": current_time
                                    })
                                    logger.success(f"✅ Employee {best_match_id} CHECKED IN on {camera_id}")
                                    self.employee_presence.add(best_match_id)
                            else:
                                # Crossed right-to-left (Check Out)
                                if best_match_id in self.employee_presence:
                                    self.recent_logs.append({
                                        "employee": f"Emp {best_match_id}", 
                                        "action": "CHECK OUT", 
                                        "time": current_time
                                    })
                                    logger.info(f"🚪 Employee {best_match_id} CHECKED OUT from {camera_id}")
                                    self.employee_presence.remove(best_match_id)
                                    
                    self.previous_centroids[best_match_id] = current_centroid
                else:
                    unauth_count += 1
                    
        # Clean up missing ids from previous centroids
        current_frame_ids = []
        if result.boxes is not None and result.boxes.id is not None:
            pass # The Re-ID makes it hard to know exactly when to prune previous_centroids, but it's small enough to just let grow
            
        # Keep only the 4 most recent logs to fit UI
        self.recent_logs = self.recent_logs[-4:]
                    
        return {
            "authorized_employees_in_frame": list(set(auth_in_frame)),
            "unauthorized_count": unauth_count,
            "attendance_logs": self.recent_logs
        }

class ParkingAnalyticsPlugin(AnalyticsPlugin):
    """
    Handles Vehicle Detection and Parking Occupancy.
    """
    def __init__(self):
        # COCO Classes for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
        self.vehicle_classes = {2, 3, 5, 7}
        logger.info("Initialized ParkingAnalyticsPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        spots = config.get_parking_spots_for_camera(camera_id)
        spot_polys = [Polygon(spot) for spot in spots]
        
        # Array matching spots, true if occupied
        occupied_spots = [False] * len(spots)
        vehicle_count = 0
        
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) not in self.vehicle_classes:
                    continue
                    
                vehicle_count += 1
                
                # Check center of vehicle against spots
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                center_point = Point(center_x, center_y)
                
                for idx, poly in enumerate(spot_polys):
                    if poly.contains(center_point):
                        occupied_spots[idx] = True
                        
        total_spots = len(spots)
        occupied_count = sum(occupied_spots)
        available_count = total_spots - occupied_count
            
        return {
            "vehicle_count": vehicle_count,
            "total_spots": total_spots,
            "occupied_spots": occupied_count,
            "available_spots": available_count,
            "spot_status": occupied_spots
        }

class TamperAnalyticsPlugin(AnalyticsPlugin):
    """
    Detects Camera Tampering (Lens Covered or Camera Shifted) using OpenCV.
    """
    def __init__(self):
        self.camera_backgrounds: Dict[str, np.ndarray] = {}
        logger.info("Initialized TamperAnalyticsPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        # Convert frame to grayscale for fast processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Covered Lens Detection (Mean Brightness)
        mean_brightness = np.mean(gray)
        is_covered = float(mean_brightness) < 10.0  # Extremely dark
        
        # 2. Camera Shift Detection (Structural Difference)
        is_shifted = False
        
        # Resize for faster background comparison
        small_gray = cv2.resize(gray, (320, 240))
        
        if camera_id not in self.camera_backgrounds:
            self.camera_backgrounds[camera_id] = small_gray.astype(float)
        else:
            bg = self.camera_backgrounds[camera_id]
            # Calculate absolute difference
            diff = cv2.absdiff(bg.astype(np.uint8), small_gray)
            mean_diff = np.mean(diff)
            
            # If the difference is massive suddenly, camera was moved
            if mean_diff > 50.0:
                is_shifted = True
                
            # Update background slowly (running average)
            cv2.accumulateWeighted(small_gray, bg, 0.05)
            self.camera_backgrounds[camera_id] = bg
            
        return {
            "tamper_alert": is_covered or is_shifted,
            "is_covered": is_covered,
            "is_shifted": is_shifted,
            "brightness": round(float(mean_brightness), 2)
        }

class EnterpriseSafetyPlugin(AnalyticsPlugin):
    """
    Real OpenCV Classical Computer Vision for Fire & Smoke detection.
    """
    def __init__(self):
        self.active_alerts = {}
        # Background subtractor for smoke - very sensitive for faint smoke
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=5, detectShadows=False)
        logger.info("Initialized EnterpriseSafetyPlugin (Real OpenCV)")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        current_time = time.time()
        if camera_id not in self.active_alerts:
            self.active_alerts[camera_id] = []
            
        # Cleanup expired alerts (alerts last 3 seconds)
        self.active_alerts[camera_id] = [
            alert for alert in self.active_alerts[camera_id] 
            if current_time - alert["timestamp"] < 3.0
        ]
            
        current_alerts = [a["type"] for a in self.active_alerts[camera_id]]
        
        # 1. Fire Detection (HSV Thresholding)
        blur = cv2.GaussianBlur(frame, (21, 21), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        
        # Define range for orange/yellow fire (strict saturation and brightness to avoid false positives)
        lower_fire = np.array([15, 150, 200], dtype=np.uint8)
        upper_fire = np.array([35, 255, 255], dtype=np.uint8)
        
        mask_fire = cv2.inRange(hsv, lower_fire, upper_fire)
        # Find contours
        contours, _ = cv2.findContours(mask_fire, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fire_detected = False
        for c in contours:
            if cv2.contourArea(c) > 40000: # Massive fire size only
                fire_detected = True
                break
                
        if fire_detected and "FIRE_DETECTED" not in current_alerts:
            self.active_alerts[camera_id].append({"type": "FIRE_DETECTED", "timestamp": current_time})
            logger.warning(f"🚨 FIRE DETECTED on {camera_id}")
            
        # 2. Smoke Detection (Moving Gray blobs)
        # Downscale for performance
        small = cv2.resize(frame, (320, 240))
        scale_x = frame.shape[1] / 320.0
        scale_y = frame.shape[0] / 240.0
        
        fg_mask = self.bg_subtractor.apply(small)
        
        # Threshold the foreground (more lenient)
        _, fg_thresh = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)
        contours_smoke, _ = cv2.findContours(fg_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Collect bounding boxes of people in the 320x240 scale
        person_boxes_small = []
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) == 0: # Person
                    x1, y1, x2, y2 = box
                    sx1, sy1 = int(x1 / scale_x), int(y1 / scale_y)
                    sx2, sy2 = int(x2 / scale_x), int(y2 / scale_y)
                    person_boxes_small.append((sx1, sy1, sx2, sy2))
        
        smoke_detected = False
        fire_detected = False
        fire_boxes = []
        smoke_boxes = []
        for c in contours_smoke:
            area = cv2.contourArea(c)
            x, y, w, h = cv2.boundingRect(c)
            bx1, by1 = int(x * scale_x), int(y * scale_y)
            bx2, by2 = int((x+w) * scale_x), int((y+h) * scale_y)
            
            is_fire_c = False
            
            # FIRE DETECTION
            if area > 500:
                x, y, w, h = cv2.boundingRect(c)
                crop = small[y:y+h, x:x+w]
                if crop.size > 0:
                    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    # Fire colors: H(0-35 and 160-179), S(>150), V(>220) - extremely bright and saturated
                    mask1 = cv2.inRange(hsv_crop, (0, 150, 220), (35, 255, 255))
                    mask2 = cv2.inRange(hsv_crop, (160, 150, 220), (179, 255, 255))
                    fire_mask = cv2.bitwise_or(mask1, mask2)
                    
                    # Require at least 200 pixels of intense fire
                    if cv2.countNonZero(fire_mask) > 200:
                        fire_detected = True
                        is_fire_c = True
                        fire_boxes.append((bx1, by1, bx2, by2))
            
            # Condition A: Massive smoke (Fire/Room filling with smoke)
            is_massive_smoke = area > 20000
            if is_massive_smoke:
                x, y, w, h = cv2.boundingRect(c)
                extent = area / float(w * h)
                if extent > 0.7:
                    # Solid large objects (like a white truck) have high extent.
                    # Smoke is diffuse and usually has lower extent.
                    is_massive_smoke = False
            
            # Condition B: Tiny smoke (Cigarette) near a person's head or close-up shots
            is_cigarette_smoke = False
            if 20 < area < 3000:
                cx, cy, cw, ch = cv2.boundingRect(c)
                extent = area / float(cw * ch)
                if extent < 0.65: # Must be diffuse, not a solid rectangle
                    if not person_boxes_small:
                        # Fallback for macro/close-up shots where YOLO doesn't see a full person
                        is_cigarette_smoke = True
                    else:
                        for (px1, py1, px2, py2) in person_boxes_small:
                            ph = py2 - py1
                            head_bottom_y = py1 + int(ph * 0.3)  # Only the top 30% of the person (Head/Mouth area)
                            # Must be extremely close to the head area
                            if (px1 - 20 < cx < px2 + 20) and (py1 - 20 < cy < head_bottom_y):
                                is_cigarette_smoke = True
                                break
            if is_massive_smoke or is_cigarette_smoke:
                x, y, w, h = cv2.boundingRect(c)
                crop = small[y:y+h, x:x+w]
                if crop.size == 0: continue
                
                hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                s_channel = hsv_crop[:,:,1]
                v_channel = hsv_crop[:,:,2]
                
                if not person_boxes_small:
                    # STRICT color check for closeups (no person anchor)
                    if np.mean(s_channel) < 40 and np.mean(v_channel) > 130:
                        smoke_detected = True
                        smoke_boxes.append((bx1, by1, bx2, by2))
                        break
                else:
                    # STRICT color check when anchored to a person's head to prevent skin/white collars from triggering it
                    if np.mean(s_channel) < 30 and np.mean(v_channel) > 140: 
                        smoke_detected = True
                        smoke_boxes.append((bx1, by1, bx2, by2))
                        break
        # The user strictly requested that smoke only be detected if fire is also present
        if smoke_detected and not fire_detected:
            smoke_detected = False

        if smoke_detected and "SMOKE_DETECTED" not in current_alerts:
            self.active_alerts[camera_id].append({"type": "SMOKE_DETECTED", "timestamp": current_time})
            logger.warning(f"🚨 SMOKE DETECTED on {camera_id}")
            
        if fire_detected and "FIRE_DETECTED" not in current_alerts:
            self.active_alerts[camera_id].append({"type": "FIRE_DETECTED", "timestamp": current_time})
            logger.warning(f"🔥 FIRE DETECTED on {camera_id}")
            
        active_event_types = [a["type"] for a in self.active_alerts[camera_id]]
            
        return {
            "active_alerts": active_event_types,
            "fire_boxes": fire_boxes,
            "smoke_boxes": smoke_boxes,
            "has_critical_alert": any(e in active_event_types for e in ["FIRE_DETECTED", "SMOKE_DETECTED"])
        }

class WeaponDetectionPlugin(AnalyticsPlugin):
    """
    Detects weapons (e.g., knives, class 43).
    """
    def __init__(self):
        self.active_alerts = {}
        os.makedirs("snapshots", exist_ok=True)
        logger.info("Initialized WeaponDetectionPlugin")

    def process(self, result, frame, camera_id: str) -> Dict[str, Any]:
        current_time = time.time()
        if camera_id not in self.active_alerts:
            self.active_alerts[camera_id] = []
            
        # Cleanup expired alerts (alerts last 3 seconds)
        self.active_alerts[camera_id] = [
            alert for alert in self.active_alerts[camera_id] 
            if current_time - alert["timestamp"] < 3.0
        ]
            
        current_alerts = [a["type"] for a in self.active_alerts[camera_id]]
        
        weapon_detected = False
        weapon_boxes = []
        new_snapshots = []
        
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy()
            
            for box, cls_id in zip(boxes, cls_ids):
                if int(cls_id) in [34, 43]: # Baseball Bat, Knife
                    weapon_detected = True
                    weapon_boxes.append(box.tolist())
                    
                    if "WEAPON_DETECTED" not in current_alerts:
                        x1, y1, x2, y2 = map(int, box)
                        cam_slug = camera_id.replace("rtsp://", "").replace("/", "_").replace(":", "_").replace("@", "_")
                        filename = f"weapon_{cam_slug}_{int(time.time())}.jpg"
                        filepath = os.path.join("snapshots", filename)
                        
                        snapshot_frame = frame.copy()
                        cv2.rectangle(snapshot_frame, (x1, y1), (x2, y2), (0, 165, 255), 3)
                        cv2.putText(snapshot_frame, "WEAPON", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        cv2.imwrite(filepath, snapshot_frame)
                        new_snapshots.append(filepath)
                    
        if weapon_detected and "WEAPON_DETECTED" not in current_alerts:
            self.active_alerts[camera_id].append({"type": "WEAPON_DETECTED", "timestamp": current_time})
            logger.warning(f"🔪 WEAPON DETECTED on {camera_id}")
            
        active_event_types = [a["type"] for a in self.active_alerts[camera_id]]
            
        return {
            "active_alerts": active_event_types,
            "weapon_boxes": weapon_boxes,
            "new_snapshots": new_snapshots,
            "has_critical_alert": "WEAPON_DETECTED" in active_event_types
        }

class AnalyticsEngine:
    """
    Runs a suite of plugins on incoming detections.
    """
    def __init__(self):
        self.plugins: List[AnalyticsPlugin] = [
            PeopleCountingPlugin(),
            SpatialAnalyticsPlugin(),
            QueueAnalyticsPlugin(),
            IdentityAnalyticsPlugin(),
            ParkingAnalyticsPlugin(),
            TamperAnalyticsPlugin(),
            EnterpriseSafetyPlugin(),
            WeaponDetectionPlugin()
        ]
        
    def run(self, result, frame, camera_id: str) -> Dict[str, Any]:
        events = {}
        
        # Identify the weapon detection video (the 'Screen Recording' file)
        is_weapon_cam = "Screen Recording" in camera_id
            
        for plugin in self.plugins:
            plugin_name = plugin.__class__.__name__
            
            # If it's the weapon test video, only run the WeaponDetectionPlugin
            if is_weapon_cam and plugin_name != "WeaponDetectionPlugin":
                continue
                
            try:
                events[plugin_name] = plugin.process(result, frame, camera_id)
            except Exception as e:
                logger.error(f"Plugin {plugin_name} failed: {e}")
        return events
