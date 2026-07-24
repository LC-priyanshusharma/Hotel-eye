from abc import ABC, abstractmethod
import numpy as np
from typing import List, Dict, Any

class IFaceEngine(ABC):
    """
    Abstract interface for Face Detection and Embeddings.
    Decouples InsightFace or other embedders (MediaPipe, DeepFace) from the business logic.
    """
    
    @abstractmethod
    def detect_and_extract(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in the frame and extracts their embeddings.
        
        Args:
            frame: A NumPy array representing the BGR image.
            
        Returns:
            A list of dictionaries, where each dict has:
            - 'bbox': list [x1, y1, x2, y2]
            - 'embedding': np.ndarray representing the face features
            - 'confidence': float (0.0 to 1.0)
        """
        pass
