import time
from datetime import datetime
from typing import List
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent
from app.plugins.visitor.repository import VisitorRepository
from app.plugins.visitor.events import VisitorEventType
from database.session import SessionLocal

# We use frame_data.faces from the asynchronous FaceWorker instead of blocking.
import threading

class VisitorPlugin(BaseDetectionPlugin):
    """
    Enterprise Visitor Identity Management Plugin.
    Recognizes visitors, matches them against the database, 
    and logs unique visits without duplicating the visitor.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        logger.info("Initialized VisitorPlugin (Tripwire).")
        
        # Thread-safe list to hold events resolved by async DB lookups
        self.pending_events = []
        self.known_visitors_cache = {}
        self.events_lock = threading.Lock()
        
        # Tracking state for tripwire
        self.track_last_seen = {} # track_id -> timestamp (for eviction)
        self.track_y_history = {} # track_id -> int (last known y2)
        self.track_face_cache = {} # track_id -> dict(embedding, crop)
        self.track_crossed = set() # track_ids that have crossed the line
        self.logged_visits = set() # track_ids that have already been logged

    @property
    def plugin_name(self) -> str:
        return "VisitorPlugin"

    def get_required_classes(self) -> List[int]:
        # 0 = person in COCO dataset
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        current_time = time.time()
        
        # Flush any events that were resolved asynchronously in background threads
        with self.events_lock:
            events = self.pending_events[:]
            self.pending_events.clear()
            
            # Evict stale tracks to prevent memory leaks
            stale_ids = [tid for tid, ts in self.track_last_seen.items() if current_time - ts > 15]
            for tid in stale_ids:
                del self.track_last_seen[tid]
                self.track_y_history.pop(tid, None)
                self.track_face_cache.pop(tid, None)
                self.track_crossed.discard(tid)
                self.logged_visits.discard(tid)
                self.known_visitors_cache.pop(tid, None)
            
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        h, w = frame_data.frame.shape[:2] if frame_data.frame is not None else (720, 1280)
        line_y = int(h * 0.5) # The physical tripwire line at 50% height
        
        person_tracks = []
        for det in frame_data.detections:
            if det.track_id is not None and det.class_id == 0:
                track_id = det.track_id
                x1, y1, x2, y2 = det.bbox
                person_tracks.append({"track_id": track_id, "bbox": [x1, y1, x2, y2]})
                self.track_last_seen[track_id] = current_time
                    
        # Process faces extracted asynchronously by FaceWorker
        for face in frame_data.faces:
            # Filter out low-confidence false positive faces (like door handles/patterns)
            if face.get("confidence", 1.0) < 0.5:
                continue
                
            matched_track_id = face.get("track_id")
            if matched_track_id is None:
                continue

            # Cache the face for this track using the perfectly synced crop from FaceWorker
            self.track_face_cache[matched_track_id] = {
                "embedding": face["embedding"].tolist(),
                "crop": face.get("crop")
            }
            
        margin_x = int(w * 0.2)
        line_start_x = margin_x
        line_end_x = w - margin_x
        
        # Check line crossings and trigger events
        for p in person_tracks:
            tid = p["track_id"]
            px1, py1, px2, py2 = p["bbox"]
            current_y = int((py1 + py2) / 2) # Center of person bounding box
            current_x = int((px1 + px2) / 2)
            
            last_y = self.track_y_history.get(tid)
            if last_y is not None:
                # Only consider it a crossing if they are horizontally within the line boundaries
                if line_start_x <= current_x <= line_end_x:
                    # Crossed going down OR crossed going up
                    if (last_y < line_y <= current_y) or (last_y > line_y >= current_y):
                        self.track_crossed.add(tid)
                        logger.info(f"Person {tid} crossed the tripwire!")
            self.track_y_history[tid] = current_y
            
            # If they crossed the line AND we have a face AND haven't logged them yet
            if tid in self.track_crossed and tid not in self.logged_visits:
                if tid in self.track_face_cache:
                    self.logged_visits.add(tid)
                    face_data = self.track_face_cache[tid]
                    logger.info(f"Triggering DB match for {tid} (Crossed line + Face acquired)")
                    
                    threading.Thread(
                        target=self._async_db_match, 
                        args=(face_data["embedding"], tid, camera_id, timestamp, face_data["crop"]),
                        daemon=True
                    ).start()
            
        # Collect drawings for the UI
        drawings = [
            {
                "type": "line",
                "coords": [[line_start_x, line_y], [line_end_x, line_y]],
                "color": [0, 255, 255], # Yellow tripwire
                "thickness": 2
            }
        ]
        
        # For every person tracked on screen, if we know who they are, draw their name!
        for p in person_tracks:
            tid = p["track_id"]
            if tid in self.known_visitors_cache:
                info = self.known_visitors_cache[tid]
                px1, py1, px2, py2 = p["bbox"]
                
                role = info.get('role', 'VISITOR')
                is_unknown = (role == 'UNKNOWN')
                
                if role == 'EMPLOYEE':
                    color = [255, 200, 50] # Cyan/Blueish for employees
                elif role == 'VISITOR':
                    color = [50, 255, 50] # Green for visitors
                else:
                    color = [50, 50, 255] # Red for unknown
                    
                text_prefix = role
                
                # Emit a drawing event for the UI!
                drawings.append({
                    "type": "text",
                    "coords": [float(px1), float(max(20, py1 - 25))],
                    "color": color,
                    "text": f"{text_prefix}: {info['name']} (ID: {info['visitor_id']})",
                    "scale": 0.6,
                    "thickness": 2
                })
                
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="VISITOR_TRACK",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={"drawings": drawings}
        ))
            
        return events

    def _async_db_match(self, embedding_list: List[float], track_id: int, camera_id: str, timestamp: float, face_crop=None):
        import cv2
        import os
        import uuid
        
        snapshot_path = None
        if face_crop is not None:
            os.makedirs("snapshots/visitors", exist_ok=True)
            snapshot_filename = f"snapshots/visitors/vis_{uuid.uuid4().hex[:8]}.jpg"
            cv2.imwrite(snapshot_filename, face_crop)
            snapshot_path = snapshot_filename

        db = SessionLocal()
        try:
            repo = VisitorRepository(db)
            match, sim = repo.find_best_match(embedding_list, threshold=0.55)
            
            if match:
                visitor_id = match.visitor_id
                
                with self.events_lock:
                    cached = self.known_visitors_cache.get(track_id)
                    if cached and cached["visitor_id"] == visitor_id:
                        # The track ID still belongs to the same person. Avoid DB spam.
                        return
                        
                # If they are registered, it's a recognition. If unknown, it's just tracking an unknown person.
                if match.status == 'REGISTERED':
                    event_type = VisitorEventType.EMPLOYEE_RECOGNIZED if match.role == 'EMPLOYEE' else VisitorEventType.VISITOR_RECOGNIZED
                else:
                    event_type = VisitorEventType.UNKNOWN_PERSON
                    # Update the UNKNOWN visitor's photo with the latest snapshot so it shows up in the UI
                    if snapshot_path:
                        match.photo = snapshot_path
                        db.commit()
                    
                conf = sim
                
                visit = repo.create_visit({
                    "visitor_id": visitor_id,
                    "entry_time": datetime.now(),
                    "camera_id": camera_id,
                    "track_id": str(track_id),
                    "confidence": conf
                })
                
                repo.log_event(
                    event_type=event_type.value if hasattr(event_type, "value") else event_type,
                    visitor_id=visitor_id,
                    visit_id=visit.visit_id,
                    camera=camera_id,
                    metadata={"similarity": conf}
                )
                
                with self.events_lock:
                    self.known_visitors_cache[track_id] = {"visitor_id": visitor_id, "name": match.name, "role": match.role}
                    # Keep cache small to avoid memory leak
                    if len(self.known_visitors_cache) > 1000:
                        self.known_visitors_cache.clear()
                            
                    self.pending_events.append(DetectionEvent(
                        plugin_name=self.plugin_name,
                        event_type=event_type.value if hasattr(event_type, "value") else event_type,
                        camera_id=camera_id,
                        timestamp=timestamp,
                        confidence=conf,
                        metadata={"visitor_id": visitor_id, "name": match.name, "track_id": track_id, "snapshot_file": snapshot_path}
                    ))
                    logger.info(f"Appended pending event: {event_type} for track {track_id}")
            else:
                unknown_visitor = repo.create_unknown_visitor(face_embedding=embedding_list, snapshot_path=snapshot_path)
                event_type = VisitorEventType.UNKNOWN_PERSON
                
                visit = repo.create_visit({
                    "visitor_id": unknown_visitor.visitor_id,
                    "entry_time": datetime.now(),
                    "camera_id": camera_id,
                    "track_id": str(track_id),
                    "confidence": 0.0
                })
                
                repo.log_event(
                    event_type=event_type.value,
                    visitor_id=unknown_visitor.visitor_id,
                    visit_id=visit.visit_id,
                    camera=camera_id
                )
                
                with self.events_lock:
                    self.known_visitors_cache[track_id] = {"visitor_id": unknown_visitor.visitor_id, "name": "Unknown", "role": "UNKNOWN"}
                    if len(self.known_visitors_cache) > 1000:
                        self.known_visitors_cache.clear()
                        
                    self.pending_events.append(DetectionEvent(
                        plugin_name=self.plugin_name,
                        event_type=event_type.value,
                        camera_id=camera_id,
                        timestamp=timestamp,
                        confidence=0.0,
                        metadata={"visitor_id": unknown_visitor.visitor_id, "track_id": track_id, "snapshot_file": snapshot_path}
                    ))
                    logger.info(f"Appended pending event: {event_type.value} for track {track_id}")
        except Exception as e:
            logger.error(f"Async DB match failed: {e}")
        finally:
            db.close()
