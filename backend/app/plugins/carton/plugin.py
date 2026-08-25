import time
import numpy as np
from typing import List
from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class CartonCountingPlugin(BaseDetectionPlugin):
    """
    Highly optimized carton (box) tracking plugin.
    Detects COCO class 28 (suitcase) which YOLO uses for cartons/boxes on the conveyor belt.
    Uses a custom centroid tracker to bypass ByteTrack's strict confidence thresholds.
    Counts cartons when they cross a vertical line.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        self.counted_cartons = set()
        self.carton_history = {} # tid -> last_x
        self.exit_line_x = None
        
        # Simple centroid tracker state
        self.next_id = 1
        self.objects = {} # id -> (cx, cy)
        self.disappeared = {} # id -> frames_disappeared
        self.max_distance = 250 # Max pixel distance to match objects on conveyor
        self.max_disappeared = 60 # Frames to keep track of a lost object

    def _compute_iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        if float(boxAArea + boxBArea - interArea) == 0:
            return 0.0
        return interArea / float(boxAArea + boxBArea - interArea)

    def _update_tracker(self, input_centroids):
        rect_to_id = {}
        if len(input_centroids) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return rect_to_id

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.objects[self.next_id] = input_centroids[i]
                self.disappeared[self.next_id] = 0
                rect_to_id[i] = self.next_id
                self.next_id += 1
            return rect_to_id

        object_ids = list(self.objects.keys())
        object_centroids = np.array(list(self.objects.values()))

        diff = object_centroids[:, np.newaxis, :] - input_centroids[np.newaxis, :, :]
        D = np.sqrt(np.sum(diff ** 2, axis=-1))

        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows, used_cols = set(), set()

        for (row, col) in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            if D[row, col] > self.max_distance:
                continue

            obj_id = object_ids[row]
            self.objects[obj_id] = input_centroids[col]
            self.disappeared[obj_id] = 0
            rect_to_id[col] = obj_id

            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(D.shape[0])) - used_rows
        unused_cols = set(range(D.shape[1])) - used_cols

        for row in unused_rows:
            obj_id = object_ids[row]
            self.disappeared[obj_id] += 1
            if self.disappeared[obj_id] > self.max_disappeared:
                del self.objects[obj_id]
                del self.disappeared[obj_id]

        for col in unused_cols:
            self.objects[self.next_id] = input_centroids[col]
            self.disappeared[self.next_id] = 0
            rect_to_id[col] = self.next_id
            self.next_id += 1

        return rect_to_id

    @property
    def plugin_name(self) -> str:
        return "CartonCountingPlugin"

    def get_required_classes(self) -> List[int]:
        # COCO classes that look like cartons/boxes:
        return [24, 26, 28, 73, 41, 69, 56, 55]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        
        if self.exit_line_x is None:
            w, h = (frame_data.frame.shape[1], frame_data.frame.shape[0]) if frame_data.frame is not None else (1280, 720)
            self.exit_line_x = w // 2
            self.exit_line_y_min = int(h * 0.5)
            self.exit_line_y_max = h
            
        drawings = []
        
        # Draw the counting line segment (not full screen)
        drawings.append({
            "type": "line",
            "coords": [[self.exit_line_x, self.exit_line_y_min], [self.exit_line_x, self.exit_line_y_max]],
            "color": [0, 255, 0],
            "thickness": 3
        })
        
        valid_boxes = []
        input_centroids = []
        
        for det in frame_data.detections:
            if det.class_id in {24, 26, 28, 73, 41, 69, 56, 55}:
                x1, y1, x2, y2 = det.bbox
                
                # Prevent multiple overlapping classes (e.g. suitcase and handbag) on the same physical carton
                overlap = False
                for existing_box in valid_boxes:
                    if self._compute_iou((x1, y1, x2, y2), existing_box) > 0.4:
                        overlap = True
                        break
                
                if not overlap:
                    valid_boxes.append((x1, y1, x2, y2))
                    input_centroids.append([(x1+x2)/2, (y1+y2)/2])
                
        input_centroids = np.array(input_centroids) if input_centroids else np.array([])
        rect_to_id = self._update_tracker(input_centroids)
        
        for i, (x1, y1, x2, y2) in enumerate(valid_boxes):
            tid = rect_to_id.get(i, f"U-{i}")
            current_x = (x1 + x2) / 2
            current_y = (y1 + y2) / 2
            
            if tid not in self.counted_cartons:
                if tid in self.carton_history:
                    last_x = self.carton_history[tid]
                    # Check if line was crossed AND if the carton is within the Y bounds of the exit line
                    if (last_x <= self.exit_line_x < current_x) or (last_x >= self.exit_line_x > current_x):
                        if self.exit_line_y_min <= current_y <= self.exit_line_y_max:
                            self.counted_cartons.add(tid)
                self.carton_history[tid] = current_x
                
            color = [0, 255, 0] if tid in self.counted_cartons else [255, 140, 0]
            
            drawings.append({
                "type": "rect",
                "coords": [x1, y1, x2, y2],
                "color": color,
                "thickness": 2
            })
            drawings.append({
                "type": "text",
                "coords": [x1, max(0, y1 - 10)],
                "color": color,
                "text": f"ID: {tid}",
                "scale": 0.8,
                "thickness": 2
            })
                    
        # Emit stats every frame to update UI instantly
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="CARTON_STATS",
            camera_id=frame_data.camera_id,
            timestamp=frame_data.timestamp,
            confidence=1.0,
            metadata={
                "total_cartons_counted": len(self.counted_cartons),
                "drawings": drawings
            }
        ))
            
        return events
