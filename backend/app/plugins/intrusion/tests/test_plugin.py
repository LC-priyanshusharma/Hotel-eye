import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.engine.base import FrameData, TrackerContext
from app.plugins.intrusion.plugin import IntrusionDetectionPlugin

class MockBoxes:
    def __init__(self, xyxy, cls, id_vals):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))
        self.id = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(id_vals)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

@patch("app.plugins.intrusion.plugin.config")
def test_intrusion_plugin_no_crash(mock_config):
    # Mock the zone to be a square from (0,0) to (100,100)
    mock_config.get_zone_for_camera.return_value = [[0, 0], [100, 0], [100, 100], [0, 100]]
    mock_config.LOITERING_THRESHOLD_SECONDS = 5.0
    
    plugin = IntrusionDetectionPlugin()
    context = TrackerContext()
    
    # Person at 50, 50 (inside zone)
    boxes = MockBoxes(
        xyxy=[[10, 10, 50, 50]],
        cls=[0],
        id_vals=[1]
    )
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0].event_type == "INTRUSION_DETECTED"
    
def test_required_classes():
    plugin = IntrusionDetectionPlugin()
    assert 0 in plugin.get_required_classes()
