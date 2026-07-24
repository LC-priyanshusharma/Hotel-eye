import cv2
import numpy as np
from typing import List, Tuple
from loguru import logger
from app.plugins.anpr.interfaces import IPlateDetector
from app.plugins.anpr.config_parser import anpr_app_config

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

class GenericYOLOPlateDetector(IPlateDetector):
    """
    Detects license plates within a larger vehicle crop or full frame using a YOLO model.
    """
    def __init__(self, model_path: str = "plate_yolo.pt", conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_path)
            except Exception as e:
                logger.error(f"Failed to load Generic YOLO Plate Detector: {e}")
                self.model = None
        else:
            self.model = None

    def detect_plates(self, image: np.ndarray) -> List[Tuple[np.ndarray, float, List[int]]]:
        plates = []
        if self.model is None:
            # Fallback heuristic
            h, w = image.shape[:2]
            y1, y2 = int(h * 0.60), h
            x1, x2 = int(w * 0.10), int(w * 0.90)
            bbox = [x1, y1, x2, y2]
            if y2 > y1 and x2 > x1:
                crop = image[y1:y2, x1:x2]
            else:
                crop = image
                bbox = [0, 0, w, h]
            
            crop = self.conditionally_enhance_plate(crop)
            return [(crop, 0.85, bbox)]

        results = self.model(image, conf=self.conf_threshold, verbose=False)
        if not results:
            return plates
            
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            crop = image[y1:y2, x1:x2]
            if crop.size > 0:
                crop = self.conditionally_enhance_plate(crop)
                plates.append((crop, conf, [x1, y1, x2, y2]))
                
        return plates

    def conditionally_enhance_plate(self, plate_img: np.ndarray) -> np.ndarray:
        """Applies enhancement ONLY when quality score is below threshold."""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Calculate blur metric (variance of Laplacian)
        quality_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Normalize quality score (approximate thresholding, > 100 is usually sharp)
        # We will use the config quality_threshold as a scaled threshold
        threshold_value = anpr_app_config.enhancement.quality_threshold * 100.0
        
        if quality_score < threshold_value:
            return self.enhance_plate(plate_img)
        return plate_img

    def enhance_plate(self, plate_img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        h_param = anpr_app_config.enhancement.denoise_h
        clip_limit = anpr_app_config.enhancement.clahe_clip_limit
        
        denoised = cv2.fastNlMeansDenoising(gray, h=h_param)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        cl1 = clahe.apply(denoised)
        
        kernel = np.array([[0, -1, 0], 
                           [-1, 5,-1], 
                           [0, -1, 0]])
        sharpened = cv2.filter2D(cl1, -1, kernel)
        enhanced_bgr = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        return enhanced_bgr


class IndianYOLOPlateDetector(GenericYOLOPlateDetector):
    """
    Optimized for Indian plates: HSRP, Single Line, Double Line, Night, Rain, Blur, Tilt.
    """
    def __init__(self, model_path: str = "indian_plate_yolo.pt", conf_threshold: float = 0.5):
        super().__init__(model_path=model_path, conf_threshold=conf_threshold)
        logger.info(f"Initialized IndianYOLOPlateDetector with model: {model_path}")
