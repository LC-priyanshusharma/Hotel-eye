import os
import mediapipe as mp
import numpy as np
from loguru import logger
from typing import List, Dict, Any

from core.config import config

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

class GestureDetector:
    def __init__(self, model_path: str = "models/gesture_recognizer.task"):
        self.model_path = model_path
        if not os.path.exists(self.model_path):
            logger.error(f"Gesture model not found at {self.model_path}")
            self.recognizer = None
            return
            
        try:
            options = GestureRecognizerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path),
                running_mode=VisionRunningMode.IMAGE,
                num_hands=config.GESTURE_MAX_HANDS,
                min_hand_detection_confidence=config.GESTURE_CONFIDENCE,
                min_hand_presence_confidence=config.GESTURE_CONFIDENCE,
                min_tracking_confidence=config.GESTURE_CONFIDENCE,
            )
            self.recognizer = GestureRecognizer.create_from_options(options)
            logger.info("Gesture model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize gesture model: {e}")
            self.recognizer = None

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        if self.recognizer is None:
            return []
            
        # Convert BGR (OpenCV) to RGB (MediaPipe)
        try:
            # MediaPipe tasks expects RGB format. frame[..., ::-1] is a quick BGR->RGB conversion.
            rgb_frame = frame[..., ::-1].copy()
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self.recognizer.recognize(mp_image)
        except Exception as e:
            logger.error(f"Gesture recognition failed: {e}")
            return []
            
        detected_hands = []
        
        if not result.gestures:
            return []
            
        h, w, _ = frame.shape
        
        for idx in range(len(result.gestures)):
            if not result.gestures[idx]:
                continue
                
            # Get the top gesture
            top_gesture = result.gestures[idx][0]
            gesture_name = top_gesture.category_name
            score = top_gesture.score
            
            logger.debug(f"Detected gesture: {gesture_name} with score: {score}")
            
            # Filter out "None" or background
            if gesture_name == "None" or gesture_name == "" or score < 0.1: # Lowered to 0.1 to debug
                continue
                
            landmarks = result.hand_landmarks[idx]
            
            # Compute bounding box from landmarks
            x_coords = [landmark.x * w for landmark in landmarks]
            y_coords = [landmark.y * h for landmark in landmarks]
            
            x_min = int(min(x_coords))
            y_min = int(min(y_coords))
            x_max = int(max(x_coords))
            y_max = int(max(y_coords))
            
            # Add padding
            padding = 20
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(w, x_max + padding)
            y_max = min(h, y_max + padding)
            
            # We don't save landmarks object directly as it may not be JSON serializable
            # Just saving as dict
            serialized_landmarks = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks]
            
            detected_hands.append({
                "gesture": gesture_name,
                "confidence": score,
                "bbox": [x_min, y_min, x_max, y_max],
                "landmarks": serialized_landmarks
            })
            
        return detected_hands
