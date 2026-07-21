import threading
import queue
import time
from typing import Optional, Any
from loguru import logger

from config.config import config
from detection.detector import YoloOpenVINODetector
from app.engine.engine import DetectionEngine
from app.engine.base import FrameData

class InferenceWorker:
    """
    Background worker thread dedicated to AI inference, tracking, and analytics.
    """
    def __init__(self, camera_id: str, input_queue: queue.Queue, output_queue: queue.Queue, gesture_queue: Optional[queue.Queue] = None, face_worker: Optional[Any] = None):
        self.camera_id = camera_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.gesture_queue = gesture_queue
        self.face_worker = face_worker
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        
        # Initialized inside the thread
        self.detector: Optional[YoloOpenVINODetector] = None
        self.detection_engine: Optional[DetectionEngine] = None
        
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
            conf = config.get_confidence_for_camera(self.camera_id)
            self.detector = YoloOpenVINODetector(conf=conf)
            self.detection_engine = DetectionEngine()
            
            # Combine classes from legacy detector config and new detection engine
            req_classes = set(self.detector.classes)
            req_classes.update(self.detection_engine.get_all_required_classes())
            self.detector.classes = list(req_classes)
        except Exception as e:
            logger.error(f"Failed to load AI components: {e}")
            return
            
        last_time = time.time()
            
        while self.is_running:
            try:
                frame = self.input_queue.get(timeout=0.1)
                self.frame_count += 1
                
                # We rely on StreamReader's bounded queue to naturally drop frames if inference is too slow,
                # ensuring we always process the freshest frame without artificial gaps that break ByteTrack.
                    
                # FPS Calculation
                current_time = time.time()
                fps = round(1.0 / max((current_time - last_time), 0.001), 1)
                last_time = current_time
                
                # Run Detection (bypass tracker if configured)
                if config.should_bypass_tracker(self.camera_id):
                    result = self.detector.detect(frame)
                else:
                    result = self.detector.detect_and_track(frame)
                
                # Fetch latest async results from FaceWorker
                faces = []
                fatigue_metrics = []
                if self.face_worker:
                    face_data = self.face_worker.get_latest_results(self.camera_id)
                    if isinstance(face_data, dict):
                        faces = face_data.get("faces", [])
                        fatigue_metrics = face_data.get("fatigue_metrics", [])
                    
                # Run New Detection Framework Plugins
                frame_data = FrameData(frame=frame, detections=result, camera_id=self.camera_id, timestamp=time.time(), faces=faces, fatigue_metrics=fatigue_metrics)
                events = self.detection_engine.run_plugins(frame_data)
                
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
                        
                # Forward to face worker if enabled
                if self.face_worker is not None and not self.face_worker.frame_queue.full():
                    try:
                        self.face_worker.frame_queue.put_nowait({
                            "camera_id": self.camera_id,
                            "frame": frame
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
