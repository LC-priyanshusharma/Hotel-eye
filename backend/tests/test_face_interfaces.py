import pytest
import numpy as np
from detection.interfaces.face import IFaceEngine

class MockFaceEngine(IFaceEngine):
    def detect_and_extract(self, frame: np.ndarray) -> list:
        return [{"bbox": [10, 10, 50, 50], "embedding": np.array([0.5, 0.5]), "confidence": 0.9}]

class IncompleteFaceEngine(IFaceEngine):
    pass

def test_face_interface():
    engine = MockFaceEngine()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    res = engine.detect_and_extract(frame)
    assert len(res) == 1
    assert "embedding" in res[0]

def test_face_incomplete():
    with pytest.raises(TypeError):
        IncompleteFaceEngine()
