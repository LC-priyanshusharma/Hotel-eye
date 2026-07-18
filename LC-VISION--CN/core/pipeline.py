import threading
import queue
import time
from typing import Optional
from loguru import logger

from core.config import config
from ai.detector import YoloOpenVINODetector
from ai.analytics import AnalyticsEngine

class InferenceWorker:
    """
    Background worker thread dedicated to AI inference, tracking, and analytics.
    """
    def __init__(self, camera_id: str, input_queue: queue.Queue, output_queue: queue.Queue, gesture_queue: Optional[queue.Queue] = None):
        self.camera_id = camera_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.gesture_queue = gesture_queue
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        
        # Initialized inside the thread
        self.detector: Optional[YoloOpenVINODetector] = None
        self.analytics: Optional[AnalyticsEngine] = None
        
        self.frame_count = 0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"Inference-{self.camera_id}")
        self._thread.start()
        logger.info(f"Started Inference Worker for camera: {self.camera_id}")

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"Stopped Inference Worker for camera: {self.camera_id}")

    def _run(self):
        logger.info(f"Inference thread {self.camera_id} starting up...")
        try:
            if "Screen Recording" in self.camera_id:
                self.detector = YoloOpenVINODetector(classes=[34], conf=0.1)
            else:
                self.detector = YoloOpenVINODetector()
            self.analytics = AnalyticsEngine()
        except Exception as e:
            logger.error(f"Failed to load AI components: {e}")
            return
            
        last_time = time.time()
            
        while self.is_running:
            try:
                frame = self.input_queue.get(timeout=0.1)
                self.frame_count += 1
                
                # Frame Skipping
                if self.frame_count % config.FRAME_SKIP != 0:
                    continue
                    
                # FPS Calculation
                current_time = time.time()
                fps = round(1.0 / max((current_time - last_time), 0.001), 1)
                last_time = current_time
                
                # Run Detection (no tracker for weapon video to bypass tracker conf thresholds)
                if "Screen Recording" in self.camera_id:
                    result = self.detector.detect(frame)
                else:
                    result = self.detector.detect_and_track(frame)
                
                # Run Analytics Plugins
                events = self.analytics.run(result, frame, self.camera_id)
                
                data_packet = {
                    "camera_id": self.camera_id,
                    "frame": frame,
                    "detections": result,
                    "events": events,
                    "fps": fps,
                    "timestamp": time.time()
                }
                
                # Forward to gesture worker if enabled
                if self.gesture_queue is not None and not self.gesture_queue.full():
                    try:
                        self.gesture_queue.put_nowait({
                            "frame": frame,
                            "detections": result,
                            "timestamp": data_packet["timestamp"]
                        })
                    except queue.Full:
                        pass
                
                if self.output_queue.full():
                    try:
                        self.output_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                try:
                    self.output_queue.put_nowait(data_packet)
                except queue.Full:
                    pass
                    
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error in inference loop {self.camera_id}: {e}")
