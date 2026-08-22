import os
import json
import redis
import threading
from typing import Dict, List, Optional, Any
from loguru import logger

from config.config import config

class CameraManager:
    """
    Singleton Manager for dynamically controlling camera pipelines.
    Instead of starting OpenCV threads, this publishes commands to Redis.
    The DeepStream pipeline (running as a separate process) listens to these commands.
    """
    def __init__(self):
        self.running_cameras: Dict[str, str] = {} # camera_id -> rtsp_url
        
        # Connect to Redis to send commands to DeepStream
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = redis.Redis.from_url(self.redis_url)
        except Exception as e:
            logger.error(f"CameraManager failed to connect to Redis: {e}")
            self.redis = None

    def start_global_workers(self):
        """Starts background workers that operate across all cameras."""
        pass

    def stop_global_workers(self):
        """Stops background workers that operate across all cameras."""
        pass

    def start_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """Publishes a START command to DeepStream via Redis."""
        if camera_id in self.running_cameras:
            logger.warning(f"Camera {camera_id} is already running!")
            return
            
        actual_path = source_path if source_path else camera_id
        
        logger.info(f"Publishing command to DeepStream to START camera: {camera_id} ({actual_path})")
        
        self.running_cameras[camera_id] = actual_path
        
        if self.redis:
            command = {
                "action": "start",
                "camera_id": camera_id,
                "url": actual_path
            }
            self.redis.publish("camera_commands", json.dumps(command))
        
        logger.info(f"Successfully requested DeepStream to start pipeline for {camera_id}")

    def stop_camera_pipeline(self, camera_id: str):
        """Publishes a STOP command to DeepStream via Redis."""
        if camera_id not in self.running_cameras:
            logger.warning(f"Camera {camera_id} is not running.")
            return

        logger.info(f"Publishing command to DeepStream to STOP camera: {camera_id}")
        del self.running_cameras[camera_id]
        
        if self.redis:
            command = {
                "action": "stop",
                "camera_id": camera_id
            }
            self.redis.publish("camera_commands", json.dumps(command))
            
        # Clear global state
        from core.state import LATEST_DATA, DATA_LOCK
        with DATA_LOCK:
            if camera_id in LATEST_DATA:
                del LATEST_DATA[camera_id]
                
    def restart_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        self.stop_camera_pipeline(camera_id)
        # DeepStream might take a second to remove the camera asynchronously
        import time
        time.sleep(1)
        self.start_camera_pipeline(camera_id, source_type, source_path)

    def get_status(self) -> Dict[str, str]:
        """Returns the connection status of all managed cameras."""
        status = {}
        for cam_id in self.running_cameras.keys():
            status[cam_id] = "Connected"
        return status

    def evaluate_auto_suspend(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """
        Evaluates whether a camera should be auto-suspended or resumed based on active plugins.
        """
        plugins = getattr(config, 'CAMERA_PLUGINS', {})
        active_plugins = plugins.get(camera_id, [])
        has_plugin = len(active_plugins) > 0
                
        is_running = camera_id in self.running_cameras
        if has_plugin and not is_running:
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
        for cam_id in list(self.running_cameras.keys()):
            self.stop_camera_pipeline(cam_id)
            
        self.stop_global_workers()

# Instantiate the Singleton instance
camera_manager = CameraManager()
