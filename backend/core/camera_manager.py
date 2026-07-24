import queue
from typing import Dict, List, Optional, Any
from loguru import logger

from config.config import config
from camera.stream_reader import StreamReader
from core.pipeline import InferenceWorker
from tracking.gesture import GestureWorker
from face.worker import FaceWorker

class CameraManager:
    """
    Singleton Manager for dynamically controlling camera pipelines.
    Follows ECC Principles: Modular, decoupled, handles camera failures independently.
    """
    def __init__(self):
        # Global Event Result Queue shared across all workers
        self.result_queue = queue.Queue(maxsize=100)
        
        # Global FaceWorker instance (can process multiple cameras)
        self.face_worker = FaceWorker()
        
        # Track running workers per camera
        self.readers: Dict[str, StreamReader] = {}
        self.workers: Dict[str, InferenceWorker] = {}
        self.gesture_workers: Dict[str, GestureWorker] = {}
        
    def start_global_workers(self):
        """Starts background workers that operate across all cameras."""
        if not self.face_worker.is_running:
            self.face_worker.start()

    def start_camera_pipeline(self, camera_url: str):
        """Initializes and starts the pipeline for a single camera dynamically."""
        if camera_url in self.workers:
            logger.warning(f"Camera {camera_url} is already running!")
            return
            
        logger.info(f"Setting up pipeline for {camera_url}")
        
        stream_reader = StreamReader(source=camera_url, buffer_size=config.FRAME_BUFFER_SIZE)
        
        observers = []
        
        gesture_worker = None
        if config.GESTURE_ENABLED:
            gesture_queue = queue.Queue(maxsize=10)
            gesture_worker = GestureWorker(
                camera_id=camera_url,
                input_queue=gesture_queue,
                result_queue=self.result_queue
            )
            observers.append(gesture_worker)
            
        observers.append(self.face_worker)
        
        inference_worker = InferenceWorker(
            camera_id=camera_url,
            input_queue=stream_reader.frame_buffer, 
            output_queue=self.result_queue,
            observers=observers,
            face_data_provider=self.face_worker
        )
        
        # Start threads safely
        stream_reader.start()
        if gesture_worker:
            gesture_worker.start()
        inference_worker.start()
        
        # Register in tracking dictionaries
        self.readers[camera_url] = stream_reader
        self.workers[camera_url] = inference_worker
        if gesture_worker:
            self.gesture_workers[camera_url] = gesture_worker
            
        logger.info(f"Successfully started pipeline for {camera_url}")

    def stop_camera_pipeline(self, camera_url: str):
        """Stops the pipeline threads for a single camera safely."""
        logger.info(f"Stopping pipeline for {camera_url}")
        
        if camera_url in self.workers:
            self.workers[camera_url].stop()
            del self.workers[camera_url]
            
        if camera_url in self.gesture_workers:
            self.gesture_workers[camera_url].stop()
            del self.gesture_workers[camera_url]
            
        if camera_url in self.readers:
            self.readers[camera_url].stop()
            del self.readers[camera_url]

    def get_status(self) -> Dict[str, str]:
        """Returns the connection status of all managed cameras."""
        status = {}
        for url, reader in self.readers.items():
            if reader.is_running and reader._cap is not None and reader._cap.isOpened():
                status[url] = "Connected"
            elif reader.is_running:
                status[url] = "Connecting/Offline"
            else:
                status[url] = "Stopped"
        return status

    def stop_all(self):
        """Stops all running cameras and global workers."""
        logger.info("Stopping all camera pipelines...")
        for url in list(self.workers.keys()):
            self.stop_camera_pipeline(url)
            
        self.face_worker.stop()

# Instantiate the Singleton instance
camera_manager = CameraManager()
