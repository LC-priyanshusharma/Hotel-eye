from typing import List, Dict, Any
from loguru import logger
from database.session import SessionLocal

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
        self.tracker_context = TrackerContext()
        logger.info(f"Initialized DetectionEngine with {len(self.plugins)} plugins.")
        
    def get_all_required_classes(self) -> List[int]:
        classes = set()
        for p in self.plugins:
            classes.update(p.get_required_classes())
        return list(classes)
        
    def run_plugins(self, frame_data: FrameData) -> Dict[str, Any]:
        import concurrent.futures
        all_events = {}
        
        def process_single_plugin(plugin):
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
