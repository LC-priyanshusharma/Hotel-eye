import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.engine.base import FrameData, TrackerContext
from app.plugins.queue.plugin import QueueAnalyticsPlugin

class MockBoxes:
    def __init__(self, xyxy, cls, id_vals):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))
        self.id = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(id_vals)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

@patch("app.plugins.queue.plugin.config")
def test_queue_plugin(mock_config):
    mock_config.get_queue_zone_for_camera.return_value = [[0,0], [100,0], [100,100], [0,100]]
    
    plugin = QueueAnalyticsPlugin()
    context = TrackerContext()
    
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
    assert events[0].event_type == "QUEUE_STATS"
    assert events[0].metadata["queue_length"] == 1
