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
        unique_ids = state["unique_ids"]
        track_history = state["track_history"]
        
        current_count = 0
        from config.config import config
        line_y = getattr(config, 'LINE_CROSSING_Y', 600)
        line_x_start = getattr(config, 'LINE_CROSSING_X_START', 750)
        line_x_end = getattr(config, 'LINE_CROSSING_X_END', 1150)
        direction = getattr(config, 'LINE_CROSSING_DIRECTION', 'down')
        
        for det in frame_data.detections:
            cls_id = det.class_id
            track_id = det.track_id
            xyxy = det.bbox
            
            if int(cls_id) == 0:
                current_count += 1
                
                # Only do line crossing and unique ID logic if we have a valid track_id
                if track_id is not None:
                    tid = int(track_id)
                    unique_ids.add(tid)
                    
                    # Calculate center Y
                    x1, y1, x2, y2 = xyxy
                    cy = (y1 + y2) / 2
                    
                    if tid not in track_history:
                        track_history[tid] = []
                    track_history[tid].append(cy)
                    
                    # Keep history small
                    if len(track_history[tid]) > 10:
                        track_history[tid].pop(0)
                        
                    # Check line crossing
                    if len(track_history[tid]) >= 2:
                        prev_y = track_history[tid][-2]
                        curr_y = track_history[tid][-1]
                        
                        # Only trigger if the person's center X is within the door boundaries
                        cx = (x1 + x2) / 2
                        is_within_x_bounds = line_x_start <= cx <= line_x_end
                        
                        crossed_down = prev_y < line_y and curr_y >= line_y
                        crossed_up = prev_y > line_y and curr_y <= line_y
                        
                        crossed = False
                        if is_within_x_bounds:
                            if direction == "down" and crossed_down:
                                crossed = True
                            elif direction == "up" and crossed_up:
                                crossed = True
                            elif direction == "both" and (crossed_down or crossed_up):
                                crossed = True
                            
                        if crossed:
                            track_history[tid] = [curr_y]
                            
                            events.append(DetectionEvent(
                                plugin_name=self.plugin_name,
                                event_type="LINE_CROSSED",
                                camera_id=camera_id,
                                timestamp=timestamp,
                                confidence=1.0,
                                metadata={
                                    "track_id": tid,
                                    "line_y": line_y,
                                    "direction_crossed": "down" if crossed_down else "up"
                                }
                            ))
                            
        # Always emit a PERSON_COUNT event for live stats and draw the line
        events.append(DetectionEvent(
            plugin_name=self.plugin_name,
            event_type="PERSON_COUNT",
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=1.0,
            metadata={
                "current_people_in_frame": current_count,
                "total_unique_people_seen": len(unique_ids),
                "drawings": [
                    {
                        "type": "line",
                        "coords": [[line_x_start, line_y], [line_x_end, line_y]],
                        "color": [0, 255, 255], # Yellow line
                        "thickness": 3
                    },
                    {
                        "type": "text",
                        "text": "Door / Black Tile",
                        "coords": [line_x_start, line_y - 10],
                        "color": [0, 255, 255],
                        "scale": 0.6,
                        "thickness": 2
                    }
                ]
            }
        ))
                    
        return events
