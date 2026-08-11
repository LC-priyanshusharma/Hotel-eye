import threading
from loguru import logger
from detection.interfaces.inference import IInferenceEngine

from detection.strategies.redis_infer import RedisInferenceStrategy

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
                return cls._cache[cache_key]
                
            logger.info(f"Instantiating Redis Inference Engine RPC Client: {backend}")
            instance = RedisInferenceStrategy(model_path, conf, classes)
                
            cls._cache[cache_key] = instance
            return instance
