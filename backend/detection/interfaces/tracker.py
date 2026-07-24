from abc import ABC, abstractmethod
import numpy as np
from typing import Any

class ITracker(ABC):
    """
    Abstract interface for object tracking algorithms (e.g., ByteTrack, BoT-SORT).
    Decouples tracking from the base detection logic.
    """
    
    @abstractmethod
    def update(self, detections: Any, frame: np.ndarray) -> Any:
        """
        Updates the tracker with new detections from the current frame.
        
        Args:
            detections: The output from the IInferenceEngine (e.g., YOLO results).
            frame: A NumPy array representing the current BGR image (some trackers need this for optical flow/Re-ID).
            
        Returns:
            A Detections object containing the persisted track IDs.
        """
        pass
