import os
from loguru import logger
from ultralytics import YOLO
import numpy as np

from detection.interfaces.inference import IInferenceEngine

class OpenVINOStrategy(IInferenceEngine):
    """
    OpenVINO inference strategy for Intel CPUs/iGPUs.
    """
    def __init__(self, model_path: str, conf: float, classes: list):
        self.conf = conf
        self.classes = classes
        
        self.ov_model_path = model_path.replace(".pt", "_openvino_model")
        
        if not os.path.exists(self.ov_model_path):
            logger.info(f"Exporting to OpenVINO: {model_path}")
            base_model = YOLO(model_path)
            base_model.export(format="openvino", half=False) 
            
        self.model = YOLO(self.ov_model_path, task='detect')
        # Warmup
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy_img, verbose=False)

    def detect(self, frame: np.ndarray):
        results = self.model(frame, conf=self.conf, classes=self.classes, verbose=False)
        return results[0]

