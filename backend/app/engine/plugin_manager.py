import os
import importlib
import inspect
from typing import List, Dict, Type
from loguru import logger

from app.engine.base import BaseDetectionPlugin

class PluginManager:
    """
    Dynamically discovers and loads plugins from the app/plugins directory.
    """
    def __init__(self, app_config, plugins_dir: str = "app/plugins"):
        self.app_config = app_config
        self.plugins_dir = plugins_dir
        
    def discover_plugins(self) -> List[BaseDetectionPlugin]:
        """
        Scans the plugins directory, imports each plugin.py module,
        and instantiates any class that inherits from BaseDetectionPlugin.
        """
        loaded_plugins = []
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins_abs_path = os.path.join(base_path, "plugins")
        
        if not os.path.exists(plugins_abs_path):
            logger.error(f"Plugin directory not found: {plugins_abs_path}")
            return loaded_plugins

        for item in os.listdir(plugins_abs_path):
            item_path = os.path.join(plugins_abs_path, item)
            
            # Check if it's a directory containing a plugin.py
            if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "plugin.py")):
                plugin_module_name = f"app.plugins.{item}.plugin"
                
                try:
                    module = importlib.import_module(plugin_module_name)
                    
                    # Find all classes in the module that inherit from BaseDetectionPlugin
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseDetectionPlugin) and obj is not BaseDetectionPlugin:
                            # Instantiate the plugin with config injection
                            plugin_instance = obj(app_config=self.app_config)
                            loaded_plugins.append(plugin_instance)
                            logger.info(f"Dynamically loaded plugin: {plugin_instance.plugin_name}")
                            
                except Exception as e:
                    logger.error(f"Failed to load plugin from {plugin_module_name}: {e}")
                    
        return loaded_plugins
