import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.engine.base import FrameData, TrackerContext
from app.plugins.attendance.plugin import AttendanceDetectionPlugin

class MockBoxes:
    def __init__(self, xyxy, cls, id_vals):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))
        self.id = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(id_vals)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

@patch("app.plugins.attendance.plugin.config")
def test_attendance_plugin_no_crash(mock_config):
    mock_config.get_checkin_line_for_camera.return_value = [[50, 0], [50, 100]]
    
    plugin = AttendanceDetectionPlugin()
    context = TrackerContext()
    
    # Person at 10, 10
    boxes = MockBoxes(
        xyxy=[[10, 10, 30, 30]],
        cls=[0],
        id_vals=[1]
    )
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0].event_type == "ATTENDANCE_STATE"
    
def test_required_classes():
    plugin = AttendanceDetectionPlugin()
    assert 0 in plugin.get_required_classes()
