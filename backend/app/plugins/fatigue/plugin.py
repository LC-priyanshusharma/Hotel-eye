import cv2
import numpy as np
import time
from typing import List, Dict, Any
from loguru import logger

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext, DetectionEvent

class FatigueDetectionPlugin(BaseDetectionPlugin):
    """
    Fatigue Detection Plugin using MediaPipe FaceMesh.
    Calculates Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR).
    Emits an event if thresholds are breached for a duration.
    """
    
    def __init__(self, app_config=None, ear_threshold: float = 0.25, mar_threshold: float = 0.6, duration_threshold: float = 2.0):
        super().__init__(app_config)
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.duration_threshold = duration_threshold
        logger.info(f"Initialized FatigueDetectionPlugin (EAR: {ear_threshold}, MAR: {mar_threshold})")
            
        # Store state (when eyes closed or mouth open started)
        # Using simple memory since we don't have bounding box IDs from mediapipe directly.
        # Ideally, we track fatigue per bounding box or globally per camera if only 1 person.
        # We will track globally per camera for simplicity.

    @property
    def plugin_name(self) -> str:
        return "FatigueDetectionPlugin"

    def get_required_classes(self) -> List[int]:
        # Requires person class (YOLO class 0) to know where to look, 
        # though MediaPipe does its own face detection.
        return [0]



    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        events = []
        if not hasattr(frame_data, "fatigue_metrics") or not frame_data.fatigue_metrics:
            return events

        # Get persistent state for this camera
        state = tracker_context.get_state(self.plugin_name, frame_data.camera_id)
        if "fatigue_start_time" not in state:
            state["fatigue_start_time"] = None
        if "yawn_start_time" not in state:
            state["yawn_start_time"] = None

        fatigue_detected = False
        yawn_detected = False
        lowest_ear = 1.0
        highest_mar = 0.0

        for metric in frame_data.fatigue_metrics:
            ear = metric.get("ear", 1.0)
            mar = metric.get("mar", 0.0)
            
            lowest_ear = min(lowest_ear, ear)
            highest_mar = max(highest_mar, mar)
            
            if ear < self.ear_threshold:
                fatigue_detected = True
                
            if mar > self.mar_threshold:
                yawn_detected = True

        # Process Fatigue (Eyes closed)
        if fatigue_detected:
            if state["fatigue_start_time"] is None:
                state["fatigue_start_time"] = frame_data.timestamp
            elif frame_data.timestamp - state["fatigue_start_time"] >= self.duration_threshold:
                events.append(DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type="FATIGUE_ALERT",
                    camera_id=frame_data.camera_id,
                    timestamp=frame_data.timestamp,
                    confidence=1.0,
                    metadata={"ear": round(lowest_ear, 3), "status": "eyes_closed"}
                ))
                # Reset to avoid continuous spam
                state["fatigue_start_time"] = None
        else:
            state["fatigue_start_time"] = None

        # Process Yawn (Mouth open)
        if yawn_detected:
            if state["yawn_start_time"] is None:
                state["yawn_start_time"] = frame_data.timestamp
            elif frame_data.timestamp - state["yawn_start_time"] >= self.duration_threshold:
                events.append(DetectionEvent(
                    plugin_name=self.plugin_name,
                    event_type="YAWN_ALERT",
                    camera_id=frame_data.camera_id,
                    timestamp=frame_data.timestamp,
                    confidence=1.0,
                    metadata={"mar": round(highest_mar, 3), "status": "yawning"}
                ))
                # Reset to avoid continuous spam
                state["yawn_start_time"] = None
        else:
            state["yawn_start_time"] = None

        return events
