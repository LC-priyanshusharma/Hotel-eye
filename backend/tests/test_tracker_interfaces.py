import pytest
import numpy as np
from typing import Any
from detection.interfaces.tracker import ITracker

class MockTracker(ITracker):
    def update(self, detections: Any, frame: np.ndarray) -> Any:
        return {"mock": "tracked_detections"}

class IncompleteTracker(ITracker):
    # Missing update method
    pass

def test_tracker_interface():
    tracker = MockTracker()
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    res = tracker.update([{"mock": "det"}], frame)
    assert res == {"mock": "tracked_detections"}

def test_tracker_incomplete():
    with pytest.raises(TypeError):
        IncompleteTracker()
