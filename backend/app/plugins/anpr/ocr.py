import time
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR is not installed. PPOCRWrapper will run in mock mode.")

class PPOCRWrapper:
    """
    Wrapper for PP-OCRv5 to extract text from license plate crops.
    Returns text, confidence, character-level confidences, and bounding boxes.
    """
    def __init__(self, use_gpu: bool = False, lang: str = "en"):
        self.use_gpu = use_gpu
        self.lang = lang
        
        if PADDLE_AVAILABLE:
            # Initialize PP-OCR model. 
            # Note: For PP-OCRv5, it is typically loaded via specific models in PaddleOCR >= 2.9
            self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, use_gpu=self.use_gpu, show_log=False)
        else:
            self.ocr = None

    def recognize(self, image_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs OCR on the given image crop.
        Returns a list of detected texts with their confidences and bounding boxes.
        """
        start_time = time.time()
        
        if not PADDLE_AVAILABLE:
            # Mock behavior for testing if library is missing
            time.sleep(0.02)
            return [{
                "text": "MH12AB1234",
                "confidence": 0.95,
                "bbox": [[0, 0], [100, 0], [100, 50], [0, 50]],
                "char_confidences": [0.95] * 10,
                "recognition_time_ms": (time.time() - start_time) * 1000
            }]

        results = self.ocr.ocr(image_crop, cls=True)
        
        extracted = []
        if results and results[0]:
            for line in results[0]:
                bbox = line[0] # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                text = line[1][0]
                confidence = line[1][1]
                
                extracted.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox,
                    "char_confidences": [float(confidence)] * len(text), # Paddle doesn't return char-level by default, we approximate or require custom inference for exact char conf.
                    "recognition_time_ms": (time.time() - start_time) * 1000
                })
                
        return extracted
