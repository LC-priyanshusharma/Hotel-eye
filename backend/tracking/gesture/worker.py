import threading
import queue
import time
from typing import Optional
from loguru import logger

from config.config import config
from .detector import GestureDetector
from .association import GesturePersonAssociator
from core.observer import IFrameObserver
from app.engine.base import FrameData

class GestureWorker(IFrameObserver):
    def __init__(self, camera_id: str, input_queue: queue.Queue, result_queue: queue.Queue):
        self.camera_id = camera_id
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.detector: Optional[GestureDetector] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"Gesture-{self.camera_id}")
        self._thread.start()
        logger.info(f"Started Gesture Worker for camera: {self.camera_id}")

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"Stopped Gesture Worker for camera: {self.camera_id}")

    def _run(self):
        logger.info(f"Gesture thread {self.camera_id} starting up...")
        try:
            self.detector = GestureDetector()
        except Exception as e:
            logger.error(f"Failed to load Gesture Detector: {e}")
            return
            
        last_time = 0
        min_interval = 1.0 / config.GESTURE_FPS if config.GESTURE_FPS > 0 else 0
        
        last_hand_raise_time = 0
            
        while self.is_running:
            try:
                packet = self.input_queue.get(timeout=0.1)
                
                # Enforce FPS limit by skipping frames
                current_time = time.time()
                if current_time - last_time < min_interval:
                    continue
                    
                last_time = current_time
                
                frame = packet["frame"]
                yolo_detections = packet["detections"]
                original_timestamp = packet["timestamp"]
                
                # Detect hands/gestures
                hands = self.detector.detect(frame)
                
                associated_hands = []
                if hands:
                    if config.GESTURE_ASSOCIATE_WITH_PERSON:
                        associated_hands = GesturePersonAssociator.associate(yolo_detections, hands)
                    else:
                        for h in hands:
                            h["track_id"] = None
                        associated_hands = hands
                        
                # Check for Hand Raise in Camera 2 or 3 (index 1 or 2)
                has_hand_raise = False
                for h in associated_hands:
                    if h["gesture"] in ["Open_Palm", "Pointing_Up", "Victory"]:
                        if h.get("person_bbox"):
                            p_y1 = h["person_bbox"][1]
                            p_y2 = h["person_bbox"][3]
                            p_height = p_y2 - p_y1
                            hy = (h["bbox"][1] + h["bbox"][3]) / 2.0
                            # Check if the hand is in the top 30% of the person's bounding box or higher
                            if hy < p_y1 + (p_height * 0.3):
                                has_hand_raise = True
                                break
                        else:
                            has_hand_raise = True
                            break
                is_lobby_or_room = config.is_hand_raise_enabled(self.camera_id)
                    
                if has_hand_raise:
                    logger.info(f"Hand Raise Detected on {self.camera_id}. is_lobby_or_room={is_lobby_or_room}")
                    
                active_alerts = ["GESTURE_DETECTED"] if associated_hands else []
                snapshot_file = None
                
                if has_hand_raise and is_lobby_or_room:
                    if current_time - last_hand_raise_time > 10.0: # 10s cooldown
                        logger.info("Triggering HAND_RAISE_DETECTED event!")
                        last_hand_raise_time = current_time
                        active_alerts.append("HAND_RAISE_DETECTED")
                        snapshot_file = None

                gesture_plugin_data = {
                    "has_critical_alert": False,
                    "active_alerts": active_alerts,
                    "gesture_events": associated_hands
                }
                if snapshot_file:
                    gesture_plugin_data["snapshot_file"] = snapshot_file
                
                event_packet = {
                    "camera_id": self.camera_id,
                    "frame": frame, 
                    "detections": yolo_detections,
                    "events": {
                        "GestureDetectionPlugin": gesture_plugin_data
                    },
                    "timestamp": original_timestamp,
                    "is_gesture_synthetic": True
                }
                
                if not self.result_queue.full():
                    self.result_queue.put_nowait(event_packet)
                    if associated_hands:
                        logger.info(f"Gesture event emitted for {self.camera_id}")
                        
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error in Gesture Worker loop: {e}")

    def on_frame_processed(self, frame_data: FrameData) -> None:
        if not self.input_queue.full():
            try:
                self.input_queue.put_nowait({
                    "frame": frame_data.frame,
                    "detections": frame_data.detections,
                    "timestamp": frame_data.timestamp
                })
            except queue.Full:
                pass
