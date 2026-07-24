from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, List
from app.engine.base import FrameData

class IFrameObserver(ABC):
    """
    Interface for decoupled asynchronous workers or observers 
    that need to process the FrameData outside the critical Inference loop.
    """
    @abstractmethod
    def on_frame_processed(self, frame_data: FrameData) -> None:
        """Called when a frame has been completely processed by the Detector and Tracker."""
        pass
