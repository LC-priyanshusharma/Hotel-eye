import pytest
import numpy as np
from app.engine.base import FrameData, TrackerContext
from app.plugins.fire.plugin import FireDetectionPlugin

def test_fire_plugin_no_crash():
    plugin = FireDetectionPlugin()
    context = TrackerContext()
    
    # Create a random RGB image
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    frame_data = FrameData(frame=frame, detections=None, camera_id="cam1", timestamp=1.0)
    events = plugin.process_frame(frame_data, context)
    
    assert isinstance(events, list)
    
    # Verify the global context was updated
    state = context.get_state("FireDetectionPlugin", "cam1")
    assert "fire_detected" in state
    assert not state["fire_detected"] # Random noise shouldn't be a 40000 area fire

def test_required_classes():
    plugin = FireDetectionPlugin()
    assert plugin.get_required_classes() == []
