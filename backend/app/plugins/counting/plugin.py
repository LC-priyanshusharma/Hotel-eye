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

        # Fixed dual parallel lines inside the camera view
        line1_y = int(fh * 0.45) # Upper line (Entry / IN line)
        line2_y = int(fh * 0.65) # Lower line (Exit / OUT line)
        line_x_start = int(fw * 0.08)
        line_x_end = int(fw * 0.92)
        
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
                    cy = (y1 + y2) / 2
                    cx = (x1 + x2) / 2
                    
                    if tid not in track_history:
                        track_history[tid] = []
                    track_history[tid].append(cy)
                    if len(track_history[tid]) > 15:
                        track_history[tid].pop(0)
                        
                    if len(track_history[tid]) >= 2 and line_x_start <= cx <= line_x_end:
                        prev_y = track_history[tid][-2]
                        curr_y = track_history[tid][-1]
                        stage = track_stages.get(tid)
                        
                        # IN Direction: Moving DOWN (Line 1 -> Line 2)
                        if prev_y < line1_y and curr_y >= line1_y:
                            track_stages[tid] = "passed_line1"
                        elif stage == "passed_line1" and prev_y < line2_y and curr_y >= line2_y:
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
                                    "out_count": state["out_count"]
                                }
                            ))
                            
                        # OUT Direction: Moving UP (Line 2 -> Line 1)
                        elif prev_y > line2_y and curr_y <= line2_y:
                            track_stages[tid] = "passed_line2"
                        elif stage == "passed_line2" and prev_y > line1_y and curr_y <= line1_y:
                            state["out_count"] += 1
                            track_stages[tid] = "completed_out"
                            events.append(DetectionEvent(
                                plugin_name=self.plugin_name,
                                event_type="LINE_CROSSED",
                                camera_id=camera_id,
                                timestamp=timestamp,
                                confidence=1.0,
                                metadata={
                                    "track_id": tid,
                                    "direction": "OUT",
                                    "in_count": state["in_count"],
                                    "out_count": state["out_count"]
                                }
                            ))

        # Always emit a PERSON_COUNT event for live footfall stats and 2 counting lines
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PERSON_COUNT",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "current_people_in_frame": current_count,
                "in_count": state["in_count"],
                "out_count": state["out_count"],
                "total_unique_people_seen": len(unique_ids),
                "drawings": [
                    {
                        "type": "line",
                        "coords": [[line_x_start, line1_y], [line_x_end, line1_y]],
                        "color": [0, 240, 255], # Cyan line 1 (IN)
                        "thickness": 2
                    },
                    {
                        "type": "line",
                        "coords": [[line_x_start, line2_y], [line_x_end, line2_y]],
                        "color": [255, 60, 180], # Pink/Magenta line 2 (OUT)
                        "thickness": 2
                    }
                ]
            }
        ))
                    
        return events
