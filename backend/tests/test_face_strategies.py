import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Attempt to import strategy, mocking insightface if it's not installed globally
with patch.dict('sys.modules', {'insightface.app': MagicMock()}):
    from detection.strategies.insightface import InsightFaceStrategy

@patch('detection.strategies.insightface.FaceAnalysis')
def test_insightface_strategy(mock_face_analysis):
    strategy = InsightFaceStrategy()
    
    # Mock the internal app directly to avoid import/patching issues
    mock_app = MagicMock()
    
    # Mock return value of .get(frame)
    mock_face = MagicMock()
    mock_face.bbox = np.array([10.0, 20.0, 50.0, 60.0])
    mock_face.embedding = np.array([0.1, 0.2, 0.3])
    mock_face.det_score = 0.99
    
    mock_app.get.return_value = [mock_face]
    strategy.app = mock_app
    
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    results = strategy.detect_and_extract(frame)
    
    assert len(results) == 1
    assert results[0]["bbox"] == [10, 20, 50, 60]
    assert np.array_equal(results[0]["embedding"], np.array([0.1, 0.2, 0.3]))
    assert results[0]["confidence"] == 0.99
