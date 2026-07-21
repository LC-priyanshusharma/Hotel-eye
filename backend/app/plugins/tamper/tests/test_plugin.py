import pytest
import numpy as np
from app.engine.base import FrameData, TrackerContext
from app.plugins.tamper.plugin import TamperDetectionPlugin

def test_tamper_plugin():
    plugin = TamperDetectionPlugin()
    context = TrackerContext()
    
    # Very dark frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=None, camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0].event_type == "TAMPER_DETECTED"
    assert events[0].metadata["is_covered"] == True
