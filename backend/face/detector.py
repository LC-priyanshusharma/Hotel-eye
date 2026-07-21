import os
import cv2
import numpy as np
from loguru import logger
from typing import List, Dict, Any, Optional

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None
    logger.error("insightface module is not installed. Face recognition will not work.")

class FaceDetector:
    """
    Wrapper around InsightFace for detecting faces and extracting embeddings.
    Runs strictly on CPU (ctx_id=-1) by default to prevent conflicts with YOLO GPU allocations.
    """
    def __init__(self, model_name: str = 'buffalo_s', det_size: tuple = (640, 640)):
        if FaceAnalysis is None:
            self.app = None
            return
            
        try:
            # We use 'buffalo_s' for faster CPU inference compared to 'buffalo_l'
            # ctx_id = -1 forces CPU execution
            self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=-1, det_size=det_size)
            logger.info(f"InsightFace model '{model_name}' initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            self.app = None

    def detect_and_extract(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in the frame and extracts their 512D embeddings.
        Returns a list of dictionaries containing bbox and embedding.
        """
        if self.app is None:
            return []
            
        try:
            # InsightFace expects BGR format (which OpenCV natively uses)
            faces = self.app.get(frame)
        except Exception as e:
            logger.error(f"Face extraction failed: {e}")
            return []
            
        results = []
        for face in faces:
            # Bounding box [x1, y1, x2, y2]
            bbox = face.bbox.astype(int).tolist()
            # 512D or 128D Embedding (numpy array)
            embedding = face.embedding
            
            # For JSON serialization, we normally convert embedding to list,
            # but we'll keep it as numpy array for fast cosine similarity later.
            results.append({
                "bbox": bbox,
                "embedding": embedding,
                "confidence": float(face.det_score)
            })
            
        return results
