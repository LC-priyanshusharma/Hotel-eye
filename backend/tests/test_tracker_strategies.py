import pytest
import numpy as np
import torch
from ultralytics import YOLO
from ultralytics.engine.results import Boxes
from detection.strategies.bytetrack import ByteTrackStrategy
from detection.strategies.botsort import BotSortStrategy

@pytest.fixture
def dummy_results():
    # Use the smallest yolo model just to generate a valid Results object schema
    model = YOLO("yolo11n.pt")
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    res = model.predict(frame)[0]
    
    # Inject a fake detection
    boxes = Boxes(torch.tensor([[10.0, 10.0, 50.0, 50.0, 0.9, 0.0]]), (640, 640))
    res.boxes = boxes
    return res, frame

def test_bytetrack_strategy(dummy_results):
    res, frame = dummy_results
    tracker = ByteTrackStrategy()
    
    tracked_res = tracker.update(res, frame)
    assert hasattr(tracked_res.boxes, 'id')
    assert tracked_res.boxes.id is not None
    assert len(tracked_res.boxes.id) == 1

def test_botsort_strategy(dummy_results):
    res, frame = dummy_results
    tracker = BotSortStrategy()
    
    tracked_res = tracker.update(res, frame)
    assert hasattr(tracked_res.boxes, 'id')
    assert tracked_res.boxes.id is not None
    assert len(tracked_res.boxes.id) == 1

def test_tracker_empty_results():
    model = YOLO("yolo11n.pt")
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    res = model.predict(frame)[0]
    # res has empty detections natively on a black frame
    
    tracker = ByteTrackStrategy()
    tracked_res = tracker.update(res, frame)
    
    assert tracked_res.boxes is None or len(tracked_res.boxes) == 0
