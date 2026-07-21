import pytest
import numpy as np
from unittest.mock import MagicMock
from app.engine.base import FrameData, TrackerContext
from app.plugins.weapon.plugin import WeaponDetectionPlugin

class MockBoxes:
    def __init__(self, xyxy, cls):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

def test_weapon_plugin_no_crash():
    plugin = WeaponDetectionPlugin()
    context = TrackerContext()
    
    # 43 is knife
    boxes = MockBoxes(
        xyxy=[[10, 10, 50, 50]],
        cls=[43]
    )
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0].event_type == "WEAPON_DETECTED"

def test_required_classes():
    plugin = WeaponDetectionPlugin()
    classes = plugin.get_required_classes()
    assert 34 in classes
    assert 43 in classes
