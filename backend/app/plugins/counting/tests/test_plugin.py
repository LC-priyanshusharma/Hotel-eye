import pytest
import numpy as np
from unittest.mock import MagicMock
from app.engine.base import FrameData, TrackerContext
from app.plugins.counting.plugin import PeopleCountingPlugin

class MockBoxes:
    def __init__(self, cls, id_vals):
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))
        self.id = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(id_vals)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

def test_counting_plugin():
    plugin = PeopleCountingPlugin()
    context = TrackerContext()
    
    # 2 People
    boxes = MockBoxes(
        cls=[0, 0, 1], # 2 people, 1 bike
        id_vals=[1, 2, 3]
    )
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0].metadata["current_people_in_frame"] == 2
