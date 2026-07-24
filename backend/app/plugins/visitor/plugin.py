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
        logger.info("Initialized VisitorPlugin (Async/Non-Blocking).")
        
        # Debounce/Cache to prevent logging a visit every single frame.
        self.active_visits = {}
        # Thread-safe list to hold events resolved by async DB lookups
        self.pending_events = []
        self.known_visitors_cache = {}
        self.events_lock = threading.Lock()

    @property
    def plugin_name(self) -> str:
        return "VisitorPlugin"

    def get_required_classes(self) -> List[int]:
        # 0 = person in COCO dataset
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        # Flush any events that were resolved asynchronously in background threads
        with self.events_lock:
            events = self.pending_events[:]
            self.pending_events.clear()
            
            # Evict stale tracks to prevent ID swapping and memory leaks
            current_time = time.time()
            stale_ids = [tid for tid, ts in self.active_visits.items() if current_time - ts > 15]
            for tid in stale_ids:
                del self.active_visits[tid]
                if tid in self.known_visitors_cache:
                    del self.known_visitors_cache[tid]
            
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        
        # Safely parse Ultralytics YOLO Results
        person_tracks = []
        if hasattr(frame_data.detections, 'boxes') and getattr(frame_data.detections.boxes, 'id', None) is not None:
            for box in frame_data.detections.boxes:
                track_id = int(box.id[0].item())
                class_id = int(box.cls[0].item())
                if class_id == 0:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    person_tracks.append({"track_id": track_id, "bbox": [x1, y1, x2, y2]})
                    
        # Process faces extracted asynchronously by FaceWorker
        for face in frame_data.faces:
            fx1, fy1, fx2, fy2 = face["bbox"]
            cx, cy = (fx1 + fx2) / 2, (fy1 + fy2) / 2
            
            # Find the person track whose bounding box contains the center of the face
            matched_track_id = int(cx + cy) # fallback
            for p in person_tracks:
                px1, py1, px2, py2 = p["bbox"]
                if px1 <= cx <= px2 and py1 <= cy <= py2:
                    matched_track_id = p["track_id"]
                    break
                    
            # Removed known_visitors_cache check so we continuously re-verify faces to detect track swaps
            if matched_track_id in self.active_visits:
                if time.time() - self.active_visits[matched_track_id] < 2.0:
                    continue
                    
            # Mark as active so we don't spawn 100 threads for the same person
            self.active_visits[matched_track_id] = time.time()
            
            embedding_list = face["embedding"].tolist()
            
            # Offload heavy DB matching to a background thread to prevent YOLO pipeline blocking
            threading.Thread(
                target=self._async_db_match, 
                args=(embedding_list, matched_track_id, camera_id, timestamp),
                daemon=True
            ).start()
            
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
                events.append(DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type="VISITOR_TRACK",
                    camera_id=camera_id,
                    timestamp=timestamp,
                    confidence=1.0,
                    metadata={
                        "drawings": [
                            {
                                "type": "text",
                                "coords": [float(px1), float(max(20, py1 - 25))],
                                "color": color,
                                "text": f"{text_prefix}: {info['name']} (ID: {info['visitor_id']})",
                                "scale": 0.6,
                                "thickness": 2
                            }
                        ]
                    }
                ))
            
        return events

    def _async_db_match(self, embedding_list: List[float], track_id: int, camera_id: str, timestamp: float):
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
                        metadata={"visitor_id": visitor_id, "name": match.name, "track_id": track_id}
                    ))
            else:
                unknown_visitor = repo.create_unknown_visitor(face_embedding=embedding_list)
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
                        metadata={"visitor_id": unknown_visitor.visitor_id, "track_id": track_id}
                    ))
        except Exception as e:
            logger.error(f"Async DB match failed: {e}")
        finally:
            db.close()
