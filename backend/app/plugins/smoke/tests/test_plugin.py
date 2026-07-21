import pytest
import numpy as np
from unittest.mock import MagicMock

from app.engine.base import FrameData, TrackerContext
from app.plugins.smoke.plugin import SmokeDetectionPlugin

class MockBoxes:
    def __init__(self, xyxy, cls):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

def test_smoke_plugin_no_crash():
    plugin = SmokeDetectionPlugin()
    context = TrackerContext()
    
    boxes = MockBoxes(
        xyxy=[[10, 10, 50, 50]],
        cls=[0] # Person
    )
    
    # Create a random RGB image
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    # Should not crash, and likely no smoke detected in random noise
    assert isinstance(events, list)

def test_required_classes():
    plugin = SmokeDetectionPlugin()
    assert 0 in plugin.get_required_classes()
