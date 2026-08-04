import threading
import queue
import time
from typing import Optional, Any, List
from loguru import logger

from config.config import config
from detection.factory import InferenceFactory
from detection.tracker_factory import TrackerFactory
from detection.interfaces.inference import IInferenceEngine
from detection.interfaces.tracker import ITracker
from app.engine.engine import DetectionEngine
from app.engine.base import FrameData
from core.observer import IFrameObserver

class InferenceWorker:
    """
    Background worker thread dedicated to AI inference, tracking, and analytics.
    """
    def __init__(self, camera_id: str, input_queue: queue.Queue, output_queue: queue.Queue, observers: Optional[List[IFrameObserver]] = None, face_data_provider: Optional[Any] = None, camera_url: str = ""):
        self.camera_id = camera_id
        self.camera_url = camera_url or camera_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.observers = observers or []
        self.face_data_provider = face_data_provider
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Initialized inside the thread
        self.detector: Optional[IInferenceEngine] = None
        self.tracker: Optional[ITracker] = None
        self.detection_engine: Optional[DetectionEngine] = None
        
        self.frame_count = 0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"Inference-{self.camera_id}")
        self._thread.start()
        logger.info(f"Started Inference Worker for camera: {self.camera_id}")

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info(f"Stopped Inference Worker for camera: {self.camera_id}")

    def _run(self):
        logger.info(f"Inference thread {self.camera_id} starting up...")
        try:
            # camera_url contains the filename (e.g. 332263_medium.mp4) which matches the config.
            self.conf = config.get_confidence_for_camera(self.camera_url)
            self.detector = InferenceFactory.create(
                backend_name=config.INFERENCE_BACKEND,
                model_path=config.MODEL_PATH,
                conf=self.conf,
                classes=[0, 2, 3, 5, 7, 34, 43]
            )
            self.tracker = TrackerFactory.create(config.TRACKER_BACKEND)
            self.detection_engine = DetectionEngine()
        except Exception as e:
            logger.error(f"Failed to load AI components: {e}")
            return
            
        last_time = time.time()
            
        while not self._stop_event.is_set():
            try:
                capture_time, frame = self.input_queue.get(timeout=0.1)
                
                # ECC Fast-Drop Algorithm:
                frames_dropped = 0
                while not self.input_queue.empty():
                    try:
                        capture_time, frame = self.input_queue.get_nowait()
                        frames_dropped += 1
                    except queue.Empty:
                        break
                        
                if frames_dropped > 0:
                    logger.debug(f"{self.camera_id}: CPU overload detected. Fast-dropped {frames_dropped} stale frames.")
                    
                self.frame_count += frames_dropped + 1
                
                # Latency Calculation
                latency_ms = int((time.time() - capture_time) * 1000)
                    
                # FPS Calculation
                current_time = time.time()
                fps = round(1.0 / max((current_time - last_time), 0.001), 1)
                last_time = current_time
                
                # Dynamically update required classes based on currently active plugins
                current_classes = self.detection_engine.get_all_required_classes(self.camera_id)
                
                if not current_classes:
                    # If no plugins are active, skip YOLO entirely to save 100% CPU and avoid empty class crashes!
                    result = []
                else:
                    # Base inference
                    if config.should_bypass_tracker(self.camera_id):
                        # No tracking, just pure detection (e.g. for fast alerts)
                        result = self.detector.detect(frame, conf=self.conf, classes=current_classes)
                    else:
                        # Detect then track
                        detections = self.detector.detect(frame, conf=self.conf, classes=current_classes)
                        result = self.tracker.update(detections, frame)
                # Fetch latest async results from FaceDataProvider
                faces = []
                if self.face_data_provider:
                    face_data = self.face_data_provider.get_latest_results(self.camera_id)
                    if isinstance(face_data, dict):
                        faces = face_data.get("faces", [])
                    
                # Run New Detection Framework Plugins
                # Pass camera_url to frame_data instead of camera_id (UUID) so config can match it
                frame_data = FrameData(
                    frame=frame, 
                    detections=result, 
                    camera_id=self.camera_id, # Match UI and backend database IDs
                    timestamp=current_time,
                    faces=faces,
                    camera_url=self.camera_url
                )
                events = self.detection_engine.run_plugins(frame_data)
                
                data_packet = {
                    "camera_id": self.camera_id,
                    "frame": frame,
                    "detections": result,
                    "events": events,
                    "fps": fps,
                    "latency_ms": latency_ms,
                    "timestamp": time.time()
                }
                
                # Notify all generic observers (Decoupled Phase C)
                for observer in self.observers:
                    observer.on_frame_processed(frame_data)
                
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
