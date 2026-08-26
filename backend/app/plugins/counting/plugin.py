from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class PeopleCountingPlugin(BaseDetectionPlugin):
    """
    Counts the total number of unique people seen by inspecting the ByteTrack IDs.
    """
    def __init__(self, app_config=None):
        super().__init__(app_config)
        logger.info("Initialized PeopleCountingPlugin")

    @property
    def plugin_name(self) -> str:
        return "PeopleCountingPlugin"

    def get_required_classes(self) -> List[int]:
        return [0]

    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        camera_id = frame_data.camera_id
        timestamp = frame_data.timestamp
        events = []
        
        state = tracker_context.get_state(self.plugin_name, camera_id)
        if "unique_ids" not in state:
            state["unique_ids"] = set()
            state["track_history"] = {}
            state["track_stages"] = {}
            state["in_count"] = 0
            state["out_count"] = 0
            
        unique_ids = state["unique_ids"]
        track_history = state["track_history"]
        track_stages = state["track_stages"]
        
        current_count = 0
        
        # Standard 1280x720 stream coordinate space matching DeepStream streammux
        fw, fh = 1280, 720

        # Exact floor line positions matching the door threshold
        line1_y = int(fh * 0.72) # Upper line (First line - Entry threshold)
        line2_y = int(fh * 0.82) # Lower line (Second line - Interior floor)
        line_x_start = int(fw * 0.20)
        line_x_end = int(fw * 0.82)
        
        for det in frame_data.detections:
            cls_id = int(det.class_id)
            track_id = det.track_id
            xyxy = det.bbox
            
            if cls_id == 0:
                current_count += 1
                
                if track_id is not None:
                    tid = int(track_id)
                    unique_ids.add(tid)
                    
                    x1, y1, x2, y2 = xyxy
                    feet_y = y2 # Track bottom of bounding box (feet position on the floor)
                    cx = (x1 + x2) / 2
                    
                    if tid not in track_history:
                        track_history[tid] = []
                    track_history[tid].append(feet_y)
                    if len(track_history[tid]) > 20:
                        track_history[tid].pop(0)
                        
                    if len(track_history[tid]) >= 2 and line_x_start <= cx <= line_x_end:
                        prev_y = track_history[tid][-2]
                        curr_y = track_history[tid][-1]
                        stage = track_stages.get(tid)
                        
                        # IN: Downward crossing over entry line threshold
                        if prev_y < line1_y <= curr_y and stage != "completed_in":
                            state["in_count"] += 1
                            track_stages[tid] = "completed_in"
                            events.append(DetectionEvent(
                                plugin_name=self.plugin_name,
                                event_type="LINE_CROSSED",
                                camera_id=camera_id,
                                timestamp=timestamp,
                                confidence=1.0,
                                metadata={
                                    "track_id": tid,
                                    "direction": "IN",
                                    "in_count": state["in_count"],
                                    "out_count": 0
                                }
                            ))

        # Always emit a PERSON_COUNT event for live footfall stats and single entry counting line
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PERSON_COUNT",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "current_people_in_frame": current_count,
                "in_count": state["in_count"],
                "out_count": 0,
                "total_unique_people_seen": len(unique_ids),
                "drawings": [
                    {
                        "type": "line",
                        "coords": [[line_x_start, line1_y], [line_x_end, line1_y]],
                        "color": [0, 240, 255], # Cyan Entry Threshold Line
                        "thickness": 2
                    }
                ]
            }
        ))
                    
        return events
