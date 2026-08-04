import queue
from typing import Dict, List, Optional, Any
from loguru import logger

from config.config import config
from camera.stream_reader import StreamReader
from camera.source import RTSPSource, FileSource, WebcamSource
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

    def stop_global_workers(self):
        """Stops background workers that operate across all cameras."""
        if self.face_worker.is_running:
            self.face_worker.stop()

    def start_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """Initializes and starts the pipeline for a single camera dynamically."""
        if camera_id in self.workers:
            logger.warning(f"Camera {camera_id} is already running!")
            return
            
        logger.info(f"Setting up pipeline for camera: {camera_id} (Type: {source_type})")
        
        # Fallback to id as path if source_path is missing (legacy)
        actual_path = source_path if source_path else camera_id
        
        # Auto-detect file sources to prevent RTSP fallback for local videos
        if str(actual_path).lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            source_type = "file"
        
        if source_type == "webcam":
            video_source = WebcamSource(actual_path)
        elif source_type in ["video_file", "file"]:
            video_source = FileSource(actual_path, loop=True)
        else:
            video_source = RTSPSource(actual_path)
            
        stream_reader = StreamReader(video_source, camera_id=camera_id, buffer_size=config.FRAME_BUFFER_SIZE)
        
        observers = []
        
        gesture_worker = None
        if config.GESTURE_ENABLED:
            gesture_queue = queue.Queue(maxsize=10)
            gesture_worker = GestureWorker(
                camera_id=camera_id,
                input_queue=gesture_queue,
                result_queue=self.result_queue
            )
            gesture_worker.start()
            observers.append(gesture_worker)
            self.gesture_workers[camera_id] = gesture_worker

        observers.append(self.face_worker)

        inference_worker = InferenceWorker(
            camera_id=camera_id,
            input_queue=stream_reader.frame_buffer, 
            output_queue=self.result_queue,
            observers=observers,
            face_data_provider=self.face_worker,
            camera_url=source_path
        )
        
        # Start threads safely
        stream_reader.start()
        inference_worker.start()
        
        # Register in tracking dictionaries
        self.readers[camera_id] = stream_reader
        self.workers[camera_id] = inference_worker
            
        logger.info(f"Successfully started pipeline for {camera_id}")

    def stop_camera_pipeline(self, camera_id: str):
        """Stops and cleans up the pipeline for a single camera. 
        Stops components in parallel for minimal latency."""
        
        import threading
        stop_threads = []
        
        def _stop_component(comp):
            if comp:
                comp.stop()

        # 1. Stop inference worker
        if camera_id in self.workers:
            t = threading.Thread(target=_stop_component, args=(self.workers[camera_id],))
            t.start()
            stop_threads.append(t)
            del self.workers[camera_id]
        
        # 2. Stop gesture worker
        if camera_id in self.gesture_workers:
            t = threading.Thread(target=_stop_component, args=(self.gesture_workers[camera_id],))
            t.start()
            stop_threads.append(t)
            del self.gesture_workers[camera_id]
            
        # 3. Stop stream reader
        if camera_id in self.readers:
            # Drain the frame buffer to free memory and unblock threads
            buf = self.readers[camera_id].frame_buffer
            while not buf.empty():
                try:
                    buf.get_nowait()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.debug(f"Error draining buffer for {camera_id}: {e}")
                    break
            t = threading.Thread(target=_stop_component, args=(self.readers[camera_id],))
            t.start()
            stop_threads.append(t)
            del self.readers[camera_id]
            
        # Wait for all stops to complete asynchronously to avoid blocking the API
        def _wait_and_clear():
            for t in stop_threads:
                t.join(timeout=2.0)
            
            # 4. Clear stale face recognition data for this camera
            if hasattr(self.face_worker, 'latest_results'):
                with self.face_worker.results_lock:
                    self.face_worker.latest_results.pop(camera_id, None)
                
            # 5. Clear global state
            from core.state import LATEST_DATA, DATA_LOCK
            with DATA_LOCK:
                if camera_id in LATEST_DATA:
                    del LATEST_DATA[camera_id]
                
            logger.info(f"Pipeline for {camera_id} fully stopped and resources released.")
            
        threading.Thread(target=_wait_and_clear, daemon=True, name=f"StopCam-{camera_id}").start()
        
    def restart_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """Hot switches a camera's source by restarting ONLY its reader thread."""
        logger.info(f"Restarting pipeline for {camera_id}...")
        self.stop_camera_pipeline(camera_id)
        self.start_camera_pipeline(camera_id, source_type, source_path)

    def get_status(self) -> Dict[str, str]:
        """Returns the connection status of all managed cameras."""
        status = {}
        for url, reader in self.readers.items():
            if reader.is_running and getattr(reader, 'source', None) and reader.source.is_opened():
                status[url] = "Connected"
            elif reader.is_running:
                status[url] = "Connecting/Offline"
            else:
                status[url] = "Stopped"
        return status

    def evaluate_auto_suspend(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """
        Evaluates whether a camera should be auto-suspended or resumed based on active plugins.
        If a camera has 0 plugins enabled, it is automatically stopped to save resources.
        If a camera has >= 1 plugins enabled, it is automatically started.
        """
        plugins = getattr(config, 'CAMERA_PLUGINS', {})
        active_plugins = plugins.get(camera_id, [])
        has_plugin = len(active_plugins) > 0
                
        is_running = camera_id in self.readers
        if has_plugin and not is_running:
            # Fallback to existing url if not provided
            if not source_path:
                from database.session import SessionLocal
                from database.repositories.camera_repository import CameraRepository
                db = SessionLocal()
                try:
                    repo = CameraRepository(db)
                    cam = repo.get_by_id(camera_id)
                    if cam:
                        source_path = getattr(cam, 'source', cam.rtsp_url)
                        source_type = getattr(cam, 'source_type', 'rtsp')
                finally:
                    db.close()
            
            if source_path:
                logger.info(f"Auto-resuming camera {camera_id} because plugins are active.")
                self.start_camera_pipeline(camera_id, source_type, source_path)
        elif not has_plugin and is_running:
            logger.info(f"Auto-suspending camera {camera_id} because 0 plugins are active.")
            self.stop_camera_pipeline(camera_id)

    def stop_all(self):
        """Stops all running cameras and global workers."""
        logger.info("Stopping all camera pipelines...")
        for url in list(self.workers.keys()):
            self.stop_camera_pipeline(url)
            
        self.stop_global_workers()

# Instantiate the Singleton instance
camera_manager = CameraManager()
