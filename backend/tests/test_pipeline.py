import pytest
import numpy as np
import time
from app.engine.engine import DetectionEngine
from app.engine.base import FrameData
import queue

def test_engine_initialization():
    engine = DetectionEngine()
    # Verify plugins were discovered and loaded dynamically
    assert len(engine.plugins) > 0
    plugin_names = [p.__class__.__name__ for p in engine.plugins]
    assert "IntrusionDetectionPlugin" in plugin_names
    assert "AttendanceDetectionPlugin" in plugin_names

def test_engine_process_frame_does_not_crash():
    engine = DetectionEngine()
    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # Pass an empty list for detections
    frame_data = FrameData(
        frame=dummy_frame, 
        detections=[], 
        camera_id="test_cam", 
        timestamp=time.time()
    )
    
    # Process it
    result = engine.run_plugins(frame_data)
    
    assert result is not None
    assert isinstance(result, dict)
