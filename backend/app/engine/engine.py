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
        # We only discover classes, we don't instantiate them yet
        self.available_plugin_classes = {
            c.__name__: c for c in self.plugin_manager.discover_plugin_classes()
        }
        
        self.active_plugins: Dict[str, BaseDetectionPlugin] = {}
        self.tracker_context = TrackerContext()
        logger.info(f"Initialized DetectionEngine with {len(self.available_plugin_classes)} available plugins.")
        
    def _sync_plugins(self, allowed_plugins: List[str]):
        """Dynamically instantiates or garbage collects plugins based on the active config."""
        from config.config import config
        
        if allowed_plugins is None:
            allowed_plugins = []
            
        # 1. Instantiate any newly enabled plugins
        for plugin_name in allowed_plugins:
            if plugin_name not in self.active_plugins and plugin_name in self.available_plugin_classes:
                try:
                    logger.info(f"Lazy-loading plugin: {plugin_name}")
                    plugin_class = self.available_plugin_classes[plugin_name]
                    plugin_instance = plugin_class(app_config=config)
                    plugin_instance.initialize()
                    self.active_plugins[plugin_name] = plugin_instance
                except Exception as e:
                    logger.error(f"Failed to lazy load {plugin_name}: {e}")
                    
        # 2. Garbage collect any disabled plugins
        current_active = list(self.active_plugins.keys())
        for plugin_name in current_active:
            if plugin_name not in allowed_plugins:
                logger.info(f"Unloading disabled plugin: {plugin_name}")
                del self.active_plugins[plugin_name]
                
    def get_all_required_classes(self, camera_id: str) -> List[int]:
        classes = set()
        allowed_plugins = config.get_allowed_plugins(camera_id)
        self._sync_plugins(allowed_plugins)
        
        for p in self.active_plugins.values():
            classes.update(p.get_required_classes())
        return list(classes)
        
    def run_plugins(self, frame_data: FrameData) -> Dict[str, Any]:
        import concurrent.futures
        import torch
        import numpy as np
        
        # Ensure boxes.data is a torch Tensor so that legacy plugins calling .cpu().numpy() don't crash
        if frame_data.detections is not None and getattr(frame_data.detections, 'boxes', None) is not None:
            if isinstance(frame_data.detections.boxes.data, np.ndarray):
                frame_data.detections.boxes.data = torch.from_numpy(frame_data.detections.boxes.data)
                
        # Note: _sync_plugins is called in get_all_required_classes right before this method in pipeline.py
        
        all_events = {}
        
        def _run_plugin(p_name: str, p_instance: BaseDetectionPlugin):
            try:
                events = p_instance.process_frame(frame_data, self.tracker_context)
                if events:
                    return p_name, [e.dict() for e in events]
            except Exception as e:
                logger.error(f"Plugin {p_name} failed during process_frame: {e}")
            return p_name, None

        if self.active_plugins:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(self.active_plugins), 8)) as executor:
                futures = [
                    executor.submit(_run_plugin, plugin_name, plugin)
                    for plugin_name, plugin in self.active_plugins.items()
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    p_name, events = future.result()
                    if events:
                        all_events[p_name] = events
                        
        return all_events
