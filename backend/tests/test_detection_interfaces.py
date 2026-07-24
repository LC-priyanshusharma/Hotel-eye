import pytest
import numpy as np
from detection.interfaces.inference import IInferenceEngine

class MockEngine(IInferenceEngine):
    def detect(self, frame: np.ndarray):
        return {"type": "detect", "frame_shape": frame.shape}

class IncompleteEngine(IInferenceEngine):
    pass
    # Missing detect

def test_inference_engine_interface():
    # Should instantiate correctly since all methods are implemented
    engine = MockEngine()
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    assert engine.detect(frame)["type"] == "detect"

def test_inference_engine_incomplete():
    # Should raise TypeError because abstract methods are missing
    with pytest.raises(TypeError):
        IncompleteEngine()
