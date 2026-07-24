import threading
import queue
import time
from loguru import logger
from typing import Dict, Any, Optional
import cv2
import numpy as np

from config.config import config
from detection.face_factory import FaceFactory
from detection.interfaces.face import IFaceEngine
from core.observer import IFrameObserver
from app.engine.base import FrameData

class FaceWorker(IFrameObserver):
    """
    Dedicated background worker for Face Recognition.
    Reads frames from a thread-safe queue and processes them asynchronously
    to avoid blocking the main YOLO tracking pipeline.
    """
    def __init__(self, queue_size: int = 10, target_fps: int = 5):
        self.frame_queue = queue.Queue(maxsize=queue_size)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.target_fps = target_fps
        
        # Shared dictionary to store the latest face results per camera
        self.latest_results: Dict[str, Any] = {}
        self.results_lock = threading.Lock()
        
        self.detector: Optional[IFaceEngine] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="FaceWorker")
        self._thread.start()
        logger.info("FaceWorker thread started.")

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("FaceWorker thread stopped.")

    def _run(self):
        logger.info("Initializing IFaceEngine inside worker thread...")
        try:
            self.detector = FaceFactory.create(config.FACE_BACKEND)
        except Exception as e:
            logger.error(f"FaceDetector failed to initialize: {e}")
            self.is_running = False
            return

        frame_interval = 1.0 / self.target_fps

        while self.is_running:
            start_time = time.time()
            
            try:
                # Non-blocking get to allow graceful shutdown
                item = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            camera_id = item.get("camera_id")
            frame = item.get("frame")
            
            if frame is None or camera_id is None:
                continue

            try:
                # Process frame for embeddings
                faces = self.detector.detect_and_extract(frame)
                
                # Update shared state
                with self.results_lock:
                    self.latest_results[camera_id] = {
                        "timestamp": time.time(),
                        "faces": faces
                    }
                    
            except Exception as e:
                logger.error(f"FaceWorker processing error on {camera_id}: {e}")
                
            # Cap FPS to save CPU
            elapsed = time.time() - start_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)

    def get_latest_results(self, camera_id: str) -> dict:
        """
        Thread-safe method for the main pipeline to grab the latest known faces.
        Returns empty dict if no recent data exists.
        """
        with self.results_lock:
            data = self.latest_results.get(camera_id)
            if not data:
                return {}
                
            # Expire old data (e.g., older than 2 seconds)
            if time.time() - data["timestamp"] > 2.0:
                return {}
                
            # Return faces
            return data

    def on_frame_processed(self, frame_data: FrameData) -> None:
        if not self.frame_queue.full():
            try:
                self.frame_queue.put_nowait({
                    "camera_id": frame_data.camera_id,
                    "frame": frame_data.frame
                })
            except queue.Full:
                pass
