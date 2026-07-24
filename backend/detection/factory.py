from loguru import logger
from detection.interfaces.inference import IInferenceEngine
from detection.strategies.openvino import OpenVINOStrategy
from detection.strategies.coreml import CoreMLStrategy
from detection.strategies.onnx import ONNXStrategy
from detection.strategies.tensorrt import TensorRTStrategy

class InferenceFactory:
    """
    Factory class to instantiate the correct IInferenceEngine strategy
    based on the configuration.
    """
    
    @staticmethod
    def create(backend_name: str, model_path: str, conf: float, classes: list) -> IInferenceEngine:
        backend = backend_name.lower()
        logger.info(f"Instantiating Inference Engine: {backend}")
        
        if backend == "openvino":
            return OpenVINOStrategy(model_path, conf, classes)
        elif backend == "coreml":
            return CoreMLStrategy(model_path, conf, classes)
        elif backend == "onnx":
            return ONNXStrategy(model_path, conf, classes)
        elif backend == "tensorrt":
            return TensorRTStrategy(model_path, conf, classes)
        else:
            raise ValueError(f"Unsupported inference backend: {backend_name}. Valid options: openvino, coreml, onnx, tensorrt")
