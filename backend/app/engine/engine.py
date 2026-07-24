from typing import List, Dict, Any
from loguru import logger
from database.session import SessionLocal
from config.config import config

from app.engine.base import BaseDetectionPlugin, FrameData, TrackerContext
from app.engine.plugin_manager import PluginManager
from models.models import CameraEvent

class DetectionEngine:
    """
    Manages and orchestrates detection plugins dynamically.
    """
    def __init__(self):
        from config.config import config
        self.plugin_manager = PluginManager(app_config=config)
        self.plugins: List[BaseDetectionPlugin] = self.plugin_manager.discover_plugins()
        for plugin in self.plugins:
            plugin.initialize()
            
        self.tracker_context = TrackerContext()
        logger.info(f"Initialized DetectionEngine with {len(self.plugins)} plugins.")
        
    def get_all_required_classes(self) -> List[int]:
        classes = set()
        for p in self.plugins:
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
                
        all_events = {}
        
        def process_single_plugin(plugin):
            allowed_plugins = config.get_allowed_plugins(frame_data.camera_id)
            if allowed_plugins and plugin.plugin_name not in allowed_plugins:
                return plugin.plugin_name, None
                
            try:
                events = plugin.process_frame(frame_data, self.tracker_context)
                if events:
                    return plugin.plugin_name, [e.dict() for e in events]
            except Exception as e:
                logger.error(f"Plugin {plugin.plugin_name} failed during process_frame: {e}")
            return plugin.plugin_name, None

        for plugin in self.plugins:
            plugin_name, events_dict = process_single_plugin(plugin)
            if events_dict:
                all_events[plugin_name] = events_dict
                
        return all_events
