import os
from loguru import logger
from ultralytics import YOLO
import numpy as np

from detection.interfaces.inference import IInferenceEngine

class ONNXStrategy(IInferenceEngine):
    """
    ONNX Runtime inference strategy.
    """
    def __init__(self, model_path: str, conf: float, classes: list):
        self.conf = conf
        self.classes = classes
        
        self.onnx_model_path = model_path.replace(".pt", ".onnx")
        
        if not os.path.exists(self.onnx_model_path):
            logger.info(f"Exporting to ONNX: {model_path}")
            base_model = YOLO(model_path)
            base_model.export(format="onnx", half=False) 
            
        self.model = YOLO(self.onnx_model_path, task='detect')
        # Warmup
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy_img, verbose=False)

    def detect(self, frame: np.ndarray):
        results = self.model(frame, conf=self.conf, classes=self.classes, verbose=False)
        return results[0]

