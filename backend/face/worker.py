import threading
import queue
import time
from loguru import logger
from typing import Dict, Any, Optional
import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None

from config.config import config
from face.detector import FaceDetector

class FaceWorker:
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
        
        # Detector is initialized inside the thread to avoid context issues
        self.detector: Optional[FaceDetector] = None
        self.mp_face_mesh = None

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
        logger.info("Initializing FaceDetector inside worker thread...")
        try:
            self.detector = FaceDetector(model_name='buffalo_s')
            if mp:
                self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=5,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
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
                
                # Process for fatigue metrics using MediaPipe
                fatigue_metrics = []
                if self.mp_face_mesh:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, _ = frame.shape
                    results = self.mp_face_mesh.process(rgb_frame)
                    
                    if results.multi_face_landmarks:
                        for landmarks in results.multi_face_landmarks:
                            # EAR indices
                            left_eye = [362, 385, 387, 263, 373, 380]
                            right_eye = [33, 160, 158, 133, 153, 144]
                            mouth = [78, 81, 13, 308, 311, 14]
                            
                            def calc_dist(p1, p2):
                                return np.linalg.norm(np.array([p1.x * w, p1.y * h]) - np.array([p2.x * w, p2.y * h]))
                                
                            def calc_ratio(pts):
                                hor = calc_dist(landmarks.landmark[pts[0]], landmarks.landmark[pts[3]])
                                v1 = calc_dist(landmarks.landmark[pts[1]], landmarks.landmark[pts[5]])
                                v2 = calc_dist(landmarks.landmark[pts[2]], landmarks.landmark[pts[4]])
                                return (v1 + v2) / (2.0 * hor) if hor > 0 else 0
                                
                            ear = (calc_ratio(left_eye) + calc_ratio(right_eye)) / 2.0
                            mar = calc_ratio(mouth)
                            fatigue_metrics.append({"ear": ear, "mar": mar})
                
                # Update shared state
                with self.results_lock:
                    self.latest_results[camera_id] = {
                        "timestamp": time.time(),
                        "faces": faces,
                        "fatigue_metrics": fatigue_metrics
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
                
            # Return both faces and fatigue_metrics
            return data
