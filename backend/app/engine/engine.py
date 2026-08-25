from typing import List, Dict, Any
from loguru import logger
from database.session import SessionLocal
from config.config import config

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext
from app.engine.plugin_manager import PluginManager
from database.models.models import CameraEvent

class DetectionEngine:
    """
    Manages and orchestrates detection plugins dynamically.
    Lazy loads plugins to save RAM/GPU and garbage collects when disabled.
    """
    def __init__(self):
        from config.config import config
        self.plugin_manager = PluginManager(app_config=config)
        self.available_plugin_classes = {
            c.__name__: c for c in self.plugin_manager.discover_plugin_classes()
        }
        
        self.active_plugins: Dict[str, BaseDetectionPlugin] = {}
        self.tracker_context = TrackerContext()
        
        # Pre-instantiate all discovered plugins on startup for low latency
        for plugin_name, plugin_class in self.available_plugin_classes.items():
            try:
                plugin_instance = plugin_class(app_config=config)
                plugin_instance.initialize()
                self.active_plugins[plugin_name] = plugin_instance
            except Exception as e:
                logger.warning(f"Plugin {plugin_name} initialization deferred: {e}")
                
        logger.info(f"Initialized DetectionEngine with {len(self.active_plugins)} active plugins.")
        
    def _sync_plugins(self, allowed_plugins: List[str]):
        """Dynamically instantiates or garbage collects plugins based on the active config."""
        from config.config import config
        
        if not allowed_plugins:
            return
            
        for plugin_name in allowed_plugins:
            if plugin_name not in self.active_plugins and plugin_name in self.available_plugin_classes:
                try:
                    plugin_class = self.available_plugin_classes[plugin_name]
                    plugin_instance = plugin_class(app_config=config)
                    plugin_instance.initialize()
                    self.active_plugins[plugin_name] = plugin_instance
                except Exception as e:
                    logger.error(f"Failed to lazy load {plugin_name}: {e}")
                    
    def get_all_required_classes(self, camera_id: str) -> List[int]:
        classes = set()
        for p in self.active_plugins.values():
            classes.update(p.get_required_classes())
        return list(classes)
        
    def run_plugins(self, frame_data: FrameData) -> Dict[str, Any]:
        all_events = {}
        if not self.active_plugins or not frame_data.detections:
            return all_events
            
        from config.config import config
        # Check if camera has specific enabled plugins list
        camera_id = frame_data.camera_id
        allowed = config.CAMERA_PLUGINS.get(camera_id)
        
        for p_name, p_instance in self.active_plugins.items():
            # If camera has an explicit list of plugins configured, skip any plugin not in that list
            if allowed is not None and p_name not in allowed:
                continue
                
            try:
                events = p_instance.process_frame(frame_data, self.tracker_context)
                if events:
                    all_events[p_name] = [e.dict() if hasattr(e, "dict") else e for e in events]
            except Exception as e:
                logger.error(f"Plugin {p_name} error: {e}")
                
        return all_events
