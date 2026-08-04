import os
from loguru import logger
from ultralytics import YOLO
import numpy as np
import threading

from detection.interfaces.inference import IInferenceEngine

class CoreMLStrategy(IInferenceEngine):
    """
    CoreML inference strategy for Apple Silicon / AMD GPUs on macOS.
    """
    def __init__(self, model_path: str, conf: float, classes: list):
        self.conf = conf
        self.classes = classes
        self.lock = threading.Lock()
        
        self.cml_model_path = model_path.replace(".pt", ".mlpackage")
        
        if not os.path.exists(self.cml_model_path):
            logger.info(f"Exporting to CoreML: {model_path}")
            base_model = YOLO(model_path)
            base_model.export(format="coreml", half=False) 
            
        self.model = YOLO(self.cml_model_path, task='detect')
        # Warmup
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy_img, verbose=False)

    def detect(self, frame: np.ndarray, conf: float = None, classes: list = None):
        conf_to_use = conf if conf is not None else self.conf
        classes_to_use = classes if classes is not None else self.classes
        with self.lock:
            results = self.model(frame, conf=conf_to_use, classes=classes_to_use, verbose=False)
        return results[0]

