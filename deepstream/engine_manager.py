import os
import fcntl
import json
import subprocess
import hashlib
from loguru import logger

class EngineManager:
    """
    Singleton Manager for TensorRT Engine building.
    Ensures that multiple camera start requests do not trigger concurrent engine builds.
    """
    def __init__(self, onnx_path: str, engine_path: str):
        self.onnx_path = onnx_path
        self.engine_path = engine_path
        self.lock_file = engine_path + ".lock"
        self.metadata_file = engine_path + ".meta.json"

    def get_onnx_hash(self) -> str:
        if not os.path.exists(self.onnx_path):
            return ""
        sha256_hash = hashlib.sha256()
        with open(self.onnx_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def is_engine_valid(self, current_hash: str) -> bool:
        if not os.path.exists(self.engine_path):
            return False
        if not os.path.exists(self.metadata_file):
            return False
            
        try:
            with open(self.metadata_file, "r") as f:
                meta = json.load(f)
            if meta.get("onnx_sha256") == current_hash:
                return True
        except Exception as e:
            logger.error(f"Error reading engine metadata: {e}")
            
        return False

    def ensure_engine_ready(self, config_path: str = None) -> bool:
        """
        Validates engine existence and checksum. If invalid, builds it ONCE.
        Returns True when engine is strictly ready.
        """
        current_hash = self.get_onnx_hash()
        if not current_hash:
            logger.error(f"ONNX model not found at {self.onnx_path}")
            return False

        logger.info(f"Acquiring lock to check/build engine: {self.lock_file}")
        with open(self.lock_file, 'w') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                if self.is_engine_valid(current_hash):
                    logger.info("TensorRT Engine is valid and ready.")
                    return True
                    
                logger.warning("TensorRT Engine missing or outdated. Building using Gst nvinfer... (This can take 10+ mins)")
                import gi
                gi.require_version('Gst', '1.0')
                from gi.repository import Gst
                
                Gst.init(None)
                nvinfer = Gst.ElementFactory.make("nvinfer", "primary-inference")
                if not nvinfer:
                    logger.error("Failed to create nvinfer element.")
                    return False
                    
                if not config_path:
                    logger.error("config_path required for DeepStream JIT build.")
                    return False
                    
                nvinfer.set_property("config-file-path", config_path)
                # Force batch-size to 4 so it builds the b4 engine
                nvinfer.set_property("batch-size", 4)
                
                logger.info("Triggering engine build via state change...")
                res = nvinfer.set_state(Gst.State.READY)
                if res == Gst.StateChangeReturn.FAILURE:
                    logger.error("Failed to set state to READY.")
                    return False
                
                logger.info("Waiting for engine build to complete...")
                ret, state, pending = nvinfer.get_state(Gst.CLOCK_TIME_NONE)
                
                nvinfer.set_state(Gst.State.NULL)
                
                if ret != Gst.StateChangeReturn.SUCCESS:
                    logger.error(f"Engine build failed: {ret}")
                    return False
                
                # Save metadata

                meta = {
                    "onnx_sha256": current_hash,
                    "precision": "fp16"
                }
                with open(self.metadata_file, "w") as f:
                    json.dump(meta, f)
                    
                logger.info("TensorRT Engine built and persisted successfully.")
                return True
                
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
                logger.info("Engine lock released.")
