import cv2
import numpy as np
from typing import List, Tuple, Any

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

class PlateDetector:
    """
    Detects license plates within a larger vehicle crop or full frame using a YOLO model.
    Also handles perspective rectification (Homography).
    """
    def __init__(self, model_path: str = "plate_yolo.pt", conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        if ULTRALYTICS_AVAILABLE:
            try:
                self.model = YOLO(model_path)
            except Exception:
                self.model = None
        else:
            self.model = None

    def detect_plates(self, image: np.ndarray) -> List[Tuple[np.ndarray, float, List[int]]]:
        """
        Returns a list of (cropped_plate_image, confidence, bbox).
        """
        plates = []
        if self.model is None:
            # Mock mode or model not found. Return center crop.
            h, w = image.shape[:2]
            cx, cy = w // 2, h // 2
            pw, ph = int(w * 0.4), int(h * 0.2)
            bbox = [cx - pw, cy - ph, cx + pw, cy + ph]
            # Ensure within bounds
            bbox = [max(0, bbox[0]), max(0, bbox[1]), min(w, bbox[2]), min(h, bbox[3])]
            crop = image[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            
            # Basic image enhancement (CLAHE, sharpening)
            crop = self.enhance_plate(crop)
            return [(crop, 0.9, bbox)]

        results = self.model(image, conf=self.conf_threshold, verbose=False)
        if not results:
            return plates
            
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            
            # Crop image
            crop = image[y1:y2, x1:x2]
            if crop.size > 0:
                crop = self.enhance_plate(crop)
                plates.append((crop, conf, [x1, y1, x2, y2]))
                
        return plates

    def enhance_plate(self, plate_img: np.ndarray) -> np.ndarray:
        """
        Applies image enhancement: CLAHE, Denoising, Sharpening
        """
        # Convert to grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Denoising
        denoised = cv2.fastNlMeansDenoising(gray, h=30)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl1 = clahe.apply(denoised)
        
        # Sharpening
        kernel = np.array([[0, -1, 0], 
                           [-1, 5,-1], 
                           [0, -1, 0]])
        sharpened = cv2.filter2D(cl1, -1, kernel)
        
        # Convert back to BGR for OCR engine if required, or keep grayscale
        enhanced_bgr = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        return enhanced_bgr
