import numpy as np
from typing import Any
from detection.interfaces.tracker import ITracker
from ultralytics.utils import IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml
import yaml

class BaseUltralyticsTrackerStrategy(ITracker):
    """
    Base class for wrapping Ultralytics internal trackers (BYTETracker, BOTSORT)
    so they can be used decoupled from the main inference loop.
    """
    def __init__(self, tracker_class, config_name: str):
        self.config_name = config_name
        cfg_path = check_yaml(config_name)
        with open(cfg_path, 'r', encoding='utf-8') as f:
            args = IterableSimpleNamespace(**yaml.safe_load(f))
        
        self.tracker = tracker_class(args)

    def update(self, detections: Any, frame: np.ndarray) -> Any:
        """
        Updates the tracker with YOLO Results object.
        """
        # If there are no detections, just return them
        if not hasattr(detections, 'boxes') or detections.boxes is None or len(detections.boxes) == 0:
            return detections
            
        # Run tracking (expects Boxes object)
        tracked = self.tracker.update(detections.boxes, frame)
        
        # If nothing is tracked, clear the boxes
        if len(tracked) == 0:
            detections.update(boxes=np.empty((0, 7)))
            return detections
            
        # Tracker returns [x1, y1, x2, y2, id, conf, cls, idx]
        # We need [x1, y1, x2, y2, id, conf, cls] for YOLO Results.update()
        if tracked.shape[1] == 8:
            tracked = tracked[:, :-1]
            
        detections.update(boxes=tracked)
        return detections
