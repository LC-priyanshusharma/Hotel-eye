from ultralytics import YOLO
import numpy as np
import torch
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml
import yaml

model = YOLO("yolo11n.pt")
res = model.predict(np.zeros((640,640,3),dtype=np.uint8))[0]

from ultralytics.engine.results import Boxes
boxes = Boxes(torch.tensor([[10, 10, 50, 50, 0.9, 0]]), (640,640))
res.boxes = boxes

cfg_path = check_yaml("bytetrack.yaml")
t = BYTETracker(IterableSimpleNamespace(**yaml.safe_load(open(cfg_path))))
tracked = t.update(res.boxes, np.zeros((640,640,3),dtype=np.uint8))
print("Output shape:", tracked.shape if hasattr(tracked, 'shape') else tracked)
print("Output values:", tracked)
