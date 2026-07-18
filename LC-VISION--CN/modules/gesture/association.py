import numpy as np
from typing import List, Dict, Any
from loguru import logger

class GesturePersonAssociator:
    @staticmethod
    def associate(tracked_persons, hands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        tracked_persons: ultralytics results.boxes (must have is_track and id)
        hands: output from GestureDetector.detect()
        
        Returns a list of gesture events with associated track_ids.
        """
        if not hands:
            return []
            
        associated_events = []
        
        persons = []
        if tracked_persons is not None and hasattr(tracked_persons, 'is_track') and getattr(tracked_persons, 'is_track', False):
            if tracked_persons.id is not None:
                boxes = tracked_persons.xyxy.cpu().numpy()
                cls_ids = tracked_persons.cls.cpu().numpy()
                track_ids = tracked_persons.id.cpu().numpy()
                
                for box, cls_id, track_id in zip(boxes, cls_ids, track_ids):
                    if int(cls_id) == 0:  # Person class
                        x1, y1, x2, y2 = box
                        center_x = (x1 + x2) / 2.0
                        center_y = (y1 + y2) / 2.0
                        persons.append({
                            "track_id": int(track_id),
                            "center": np.array([center_x, center_y]),
                            "bbox": [x1, y1, x2, y2]
                        })
                    
        for hand in hands:
            hx1, hy1, hx2, hy2 = hand["bbox"]
            hand_center = np.array([(hx1 + hx2) / 2.0, (hy1 + hy2) / 2.0])
            
            best_track_id = None
            best_person_bbox = None
            min_dist = float('inf')
            
            for p in persons:
                dist = np.linalg.norm(p["center"] - hand_center)
                if dist < min_dist:
                    min_dist = dist
                    best_track_id = p["track_id"]
                    best_person_bbox = p["bbox"]
                    
            if best_track_id is not None:
                logger.info(f"Gesture associated: {hand['gesture']} -> Person {best_track_id}")
                hand["track_id"] = best_track_id
                hand["person_bbox"] = best_person_bbox
            else:
                logger.debug(f"Gesture {hand['gesture']} detected, but no person found to associate.")
                hand["track_id"] = None
                hand["person_bbox"] = None
                
            associated_events.append(hand)
            
        return associated_events
