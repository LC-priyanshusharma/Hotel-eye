import pytest
import numpy as np
from unittest.mock import MagicMock

from app.engine.base import FrameData, TrackerContext
from app.plugins.garbage.plugin import GarbageDetectionPlugin
from app.plugins.garbage.config import garbage_config

# Set small dwell time for testing
garbage_config.GARBAGE_DWELL_TIME_SECONDS = 2.0

class MockBoxes:
    def __init__(self, xyxy, cls, conf, id):
        self.xyxy = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(xyxy)))))
        self.cls = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(cls)))))
        self.conf = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(conf)))))
        self.id = MagicMock(cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=np.array(id)))))

class MockDetections:
    def __init__(self, boxes):
        self.boxes = boxes

def test_dwell_time_logic():
    plugin = GarbageDetectionPlugin()
    context = TrackerContext()
    
    # Frame 1: Detection at t=0
    boxes = MockBoxes(
        xyxy=[[10, 10, 50, 50]],
        cls=[0], # mapped to plastic bottle
        conf=[0.9],
        id=[1]
    )
    frame_data_1 = FrameData(frame=np.zeros((100, 100, 3), dtype=np.uint8), detections=MockDetections(boxes), camera_id="cam1", timestamp=0.0)
    
    events_1 = plugin.process_frame(frame_data_1, context)
    assert len(events_1) == 0 # Dwell time not met
    
    # Frame 2: Detection at t=1.0 (Still under 2.0s)
    frame_data_2 = FrameData(frame=np.zeros((100, 100, 3), dtype=np.uint8), detections=MockDetections(boxes), camera_id="cam1", timestamp=1.0)
    events_2 = plugin.process_frame(frame_data_2, context)
    assert len(events_2) == 0
    
    # Frame 3: Detection at t=2.5 (Threshold met)
    frame_data_3 = FrameData(frame=np.zeros((100, 100, 3), dtype=np.uint8), detections=MockDetections(boxes), camera_id="cam1", timestamp=2.5)
    events_3 = plugin.process_frame(frame_data_3, context)
    assert len(events_3) == 1
    
    assert events_3[0].event_type == "GARBAGE_DETECTED"
    assert events_3[0].metadata["category"] == "plastic bottle"
    assert events_3[0].metadata["duration_seconds"] >= 2.5
    
    # Frame 4: Detection at t=3.0 (Already alerted, should not alert again)
    frame_data_4 = FrameData(frame=np.zeros((100, 100, 3)), detections=MockDetections(boxes), camera_id="cam1", timestamp=3.0)
    events_4 = plugin.process_frame(frame_data_4, context)
    assert len(events_4) == 0
