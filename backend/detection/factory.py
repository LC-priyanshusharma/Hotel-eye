import threading
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
    
    _cache = {}
    _lock = threading.Lock()
    
    @classmethod
    def create(cls, backend_name: str, model_path: str, conf: float, classes: list) -> IInferenceEngine:
        backend = backend_name.lower()
        cache_key = f"{backend}_{model_path}"
        
        with cls._lock:
            if cache_key in cls._cache:
                logger.debug(f"Using cached Inference Engine: {backend} for {model_path}")
                return cls._cache[cache_key]
                
            logger.info(f"Instantiating new Inference Engine: {backend}")
            
            if backend == "openvino":
                instance = OpenVINOStrategy(model_path, conf, classes)
            elif backend == "coreml":
                try:
                    instance = CoreMLStrategy(model_path, conf, classes)
                except Exception as e:
                    logger.warning(f"Failed to initialize CoreML ({e}). Falling back to ONNX CPU provider.")
                    instance = ONNXStrategy(model_path, conf, classes)
            elif backend == "onnx":
                instance = ONNXStrategy(model_path, conf, classes)
            elif backend == "tensorrt":
                instance = TensorRTStrategy(model_path, conf, classes)
            else:
                raise ValueError(f"Unsupported inference backend: {backend_name}. Valid options: openvino, coreml, onnx, tensorrt")
                
            cls._cache[cache_key] = instance
            return instance
