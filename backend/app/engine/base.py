from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dataclasses import dataclass, field
import numpy as np

class DetectionEvent(BaseModel):
    plugin_name: str
    event_type: str
    camera_id: str
    timestamp: float
    confidence: float
    metadata: Dict[str, Any] = {}
    snapshot_path: Optional[str] = None

@dataclass
class FrameData:
    frame: np.ndarray
    detections: List[Dict[str, Any]]
    camera_id: str
    timestamp: float
    faces: List[Any] = field(default_factory=list)
    fatigue_metrics: List[Dict[str, float]] = field(default_factory=list)

class TrackerContext:
    # A simple context object passed to plugins allowing them to store
    # and retrieve plugin-specific and camera-specific state globally.
    def __init__(self):
        self._state: Dict[str, Dict[str, Any]] = {}
        
    def get_state(self, plugin_name: str, camera_id: str) -> Dict[str, Any]:
        if plugin_name not in self._state:
            self._state[plugin_name] = {}
        if camera_id not in self._state[plugin_name]:
            self._state[plugin_name][camera_id] = {}
        return self._state[plugin_name][camera_id]

class BaseDetectionPlugin(ABC):
    """
    Base class that all Detection Plugins must inherit from.
    """
    def __init__(self, app_config=None):
        self.config = app_config
        pass
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Return the unique name of this plugin."""
        pass

    @abstractmethod
    def get_required_classes(self) -> List[int]:
        """Return the YOLO class indices this plugin requires."""
        pass
        
    @abstractmethod
    def process_frame(self, frame_data: FrameData, tracker_context: TrackerContext) -> List[DetectionEvent]:
        """
        Process a single frame's detections and return any generated events.
        """
        pass
