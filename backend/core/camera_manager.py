import json
import redis
from typing import Dict, List, Optional
from loguru import logger

from config.config import config

class CameraManager:
    """
    Singleton Manager for dynamically controlling camera pipelines.
    Refactored for DeepStream: Instead of spawning local OpenCV threads,
    this manager publishes Redis messages to the deepstream-worker container.
    """
    def __init__(self):
        self.redis_client = redis.Redis.from_url(config.REDIS_URL)
        
        # Track running cameras (just metadata now, no local threads)
        self.running_cameras: Dict[str, dict] = {}
        
    def start_global_workers(self):
        pass

    def stop_global_workers(self):
        pass

    def start_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        """Initializes and starts the pipeline for a single camera dynamically."""
        if camera_id in self.running_cameras:
            logger.warning(f"Camera {camera_id} is already running in DeepStream!")
            return
            
        logger.info(f"Commanding DeepStream to start camera: {camera_id}")
        
        actual_path = source_path if source_path else camera_id
        
        # Auto-detect file sources
        if str(actual_path).lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            actual_path = f"file://{actual_path}"
            
        self.running_cameras[camera_id] = {"url": actual_path}
        
        # Register the stream with MediaMTX so frontend can proxy via WebRTC
        try:
            import requests
            import re
            # Clean camera ID to match frontend's encodeURIComponent(cameraId.replace(/[^a-zA-Z0-9_-]/g, ''))
            clean_camera_id = re.sub(r'[^a-zA-Z0-9_-]', '', camera_id)
            mtx_url = f"http://mediamtx:9997/v3/config/paths/add/{clean_camera_id}"
            requests.post(mtx_url, json={
                "source": actual_path,
                "sourceOnDemand": True
            }, timeout=2)
            logger.info(f"Registered {clean_camera_id} with MediaMTX.")
        except Exception as e:
            logger.error(f"Failed to register camera {camera_id} with MediaMTX: {e}")
        
        # Publish to DeepStream manager
        self.redis_client.publish("logiceye:commands", json.dumps({
            "command": "start_camera",
            "camera_id": camera_id,
            "url": actual_path
        }))
            
        logger.info(f"Successfully sent start command for {camera_id}")

    def stop_camera_pipeline(self, camera_id: str):
        """Stops and cleans up the pipeline for a single camera."""
        if camera_id in self.running_cameras:
            del self.running_cameras[camera_id]
            
            # Remove stream from MediaMTX
            try:
                import requests
                import re
                clean_camera_id = re.sub(r'[^a-zA-Z0-9_-]', '', camera_id)
                mtx_url = f"http://mediamtx:9997/v3/config/paths/remove/{clean_camera_id}"
                requests.post(mtx_url, timeout=2)
                logger.info(f"Removed {clean_camera_id} from MediaMTX.")
            except Exception as e:
                logger.error(f"Failed to remove camera {camera_id} from MediaMTX: {e}")
                
            self.redis_client.publish("logiceye:commands", json.dumps({
                "command": "stop_camera",
                "camera_id": camera_id
            }))
            
            # Clear global state
            from core.state import LATEST_DATA, DATA_LOCK
            with DATA_LOCK:
                if camera_id in LATEST_DATA:
                    del LATEST_DATA[camera_id]
                    
            logger.info(f"Sent stop command for {camera_id} to DeepStream.")
        
    def restart_camera_pipeline(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
        self.stop_camera_pipeline(camera_id)
        self.start_camera_pipeline(camera_id, source_type, source_path)

    def get_status(self) -> Dict[str, str]:
        """Returns the connection status of all managed cameras."""
        return {cam_id: "Connected (DeepStream)" for cam_id in self.running_cameras.keys()}

    def evaluate_auto_suspend(self, camera_id: str, source_type: str = "rtsp", source_path: str = None):
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
        logger.info("Stopping all camera pipelines in DeepStream...")
        for cam_id in list(self.running_cameras.keys()):
            self.stop_camera_pipeline(cam_id)

# Instantiate the Singleton instance
camera_manager = CameraManager()

