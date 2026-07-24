from abc import ABC, abstractmethod
import numpy as np
from typing import Any

class IInferenceEngine(ABC):
    """
    Abstract interface for object detection and tracking.
    Implementations of this interface (Strategies) abstract the hardware
    and the inference library (OpenVINO, TensorRT, CoreML, etc.) away from the business logic.
    """
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> Any:
        """
        Performs object detection on the provided frame.
        
        Args:
            frame: A NumPy array representing the BGR image.
            
        Returns:
            Detections object containing bounding boxes, confidences, and classes.
        """
        pass

