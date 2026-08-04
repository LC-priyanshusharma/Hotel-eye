import cv2
import numpy as np
import threading

class StreamRenderer:
    """
    Handles all OpenCV drawing operations for the MJPEG stream.
    Isolates drawing logic from the FastAPI routing logic.
    """
    def __init__(self):
        self.camera_map_lock = threading.Lock()
        self.camera_id_maps = {}
        self.camera_available_ids = {}

    def render_frame(self, camera_id: str, packet: dict) -> np.ndarray:
        result = packet.get("detections")
        
        # 1. Base drawing (Legacy plugins or no YOLO plugins)
        if "hlo.mp4" in camera_id or result is None or isinstance(result, list):
            annotated_frame = packet["frame"].copy()
        else:
            annotated_frame = result.plot(labels=False, conf=False).copy()
        
        # Override tracker IDs to just show 1, 2, 3... for the people currently in the frame
        if hasattr(result, 'boxes') and result.boxes is not None and getattr(result.boxes, 'is_track', False) and "hlo.mp4" not in camera_id:
            with self.camera_map_lock:
                if camera_id not in self.camera_id_maps:
                    self.camera_id_maps[camera_id] = {}
                    self.camera_available_ids[camera_id] = set(range(1, 10000))
                    
                cam_map = self.camera_id_maps[camera_id]
                cam_avail = self.camera_available_ids[camera_id]
                current_track_ids = result.boxes.id.cpu().numpy().tolist() if result.boxes.id is not None else []
                
                local_ids = []
                for tid in current_track_ids:
                    if tid not in cam_map:
                        sid = min(cam_avail)
                        cam_avail.remove(sid)
                        cam_map[tid] = sid
                    local_ids.append(cam_map[tid])
                    
                for tid in list(cam_map.keys()):
                    if tid not in current_track_ids:
                        cam_avail.add(cam_map.pop(tid))
                    
            # Draw labels manually using OpenCV
            for box, sid in zip(result.boxes.xyxy.cpu().numpy(), local_ids):
                x1, y1, x2, y2 = map(int, box)
                label = f"id {sid}"
                # Draw small background rectangle for text
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated_frame, (x1, y1 - h - 10), (x1 + w + 10, y1), (255, 50, 50), -1)
                cv2.putText(annotated_frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw Gesture Landmarks if available
        if "GestureDetectionPlugin" in packet.get("events", {}):
            gesture_data = packet["events"]["GestureDetectionPlugin"]
            for hand in gesture_data.get("gesture_events", []):
                landmarks = hand.get("landmarks", [])
                if landmarks:
                    import mediapipe as mp
                    from mediapipe.framework.formats import landmark_pb2
                    
                    mp_drawing = mp.solutions.drawing_utils
                    mp_hands = mp.solutions.hands
                    
                    hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                    hand_landmarks_proto.landmark.extend([
                        landmark_pb2.NormalizedLandmark(x=lm["x"], y=lm["y"], z=lm["z"]) 
                        for lm in landmarks
                    ])
                    
                    mp_drawing.draw_landmarks(
                        annotated_frame,
                        hand_landmarks_proto,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(255, 105, 180), thickness=2, circle_radius=4),
                        mp_drawing.DrawingSpec(color=(255, 105, 180), thickness=2)
                    )
                        
        # Draw declarative UI from New Detection Plugins
        for plugin_name, events in packet.get("events", {}).items():
            if isinstance(events, list): # New plugins return lists of DetectionEvent dicts
                for event in events:
                    metadata = event.get("metadata", {})
                    drawings = metadata.get("drawings", [])
                    for draw in drawings:
                        if draw["type"] == "rect":
                            x1, y1, x2, y2 = draw["coords"]
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thick)
                        elif draw["type"] == "text":
                            x, y = draw["coords"]
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            scale = draw.get("scale", 0.7)
                            text = draw.get("text", "")
                            cv2.putText(annotated_frame, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)
                        elif draw["type"] == "line":
                            pt1, pt2 = draw["coords"]
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            cv2.line(annotated_frame, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), color, thick)
                        elif draw["type"] == "poly":
                            pts = np.array(draw["coords"], np.int32).reshape((-1, 1, 2))
                            color = tuple(draw["color"])
                            thick = draw.get("thickness", 2)
                            opacity = draw.get("opacity", 0.0)
                            
                            if opacity > 0:
                                overlay = annotated_frame.copy()
                                cv2.fillPoly(overlay, [pts], color)
                                cv2.addWeighted(overlay, opacity, annotated_frame, 1 - opacity, 0, annotated_frame)
                                
                            if thick > 0:
                                cv2.polylines(annotated_frame, [pts], isClosed=True, color=color, thickness=thick)
                            
        return annotated_frame

renderer = StreamRenderer()
