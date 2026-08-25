import time
import cv2
import numpy as np
from typing import Dict, Any, List
from loguru import logger
from app.plugins.anpr.interfaces import IOCR

class EasyOCRProvider(IOCR):
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        try:
            import easyocr
            self.reader = easyocr.Reader(["en"], gpu=use_gpu)
            logger.info(f"Initialized EasyOCRProvider (gpu={self.use_gpu})")
        except Exception as e:
            self.reader = None
            logger.error(f"Failed to initialize EasyOCR: {e}")

    def recognize(self, image_crop: np.ndarray) -> List[Dict[str, Any]]:
        start_time = time.time()
        extracted = []
        
        if self.reader is None or image_crop is None or not isinstance(image_crop, np.ndarray) or image_crop.size == 0:
            return extracted
            
        try:
            # High-accuracy bicubic upscaling to height 120px for clear text recognition
            h, w = image_crop.shape[:2]
            scale = 120.0 / max(1, h)
            target_w = max(100, int(w * scale))
            upscaled = cv2.resize(image_crop, (target_w, 120), interpolation=cv2.INTER_CUBIC)

            results = self.reader.readtext(upscaled, detail=1, allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-")
            
            for (bbox, text, prob) in results:
                cleaned = text.replace(" ", "").replace("-", "").upper()
                if len(cleaned) >= 2:
                    extracted.append({
                        "text": cleaned,
                        "confidence": float(prob),
                        "bbox": bbox,
                        "char_confidences": [float(prob)] * len(cleaned),
                        "recognition_time_ms": (time.time() - start_time) * 1000
                    })
        except Exception as e:
            logger.error(f"EasyOCR Error: {e}")
            
        return extracted
