from ultralytics.trackers.byte_tracker import BYTETracker
from detection.strategies.base_tracker import BaseUltralyticsTrackerStrategy

class ByteTrackStrategy(BaseUltralyticsTrackerStrategy):
    """
    ByteTrack implementation of the ITracker interface.
    Uses the underlying Ultralytics BYTETracker for performance.
    """
    def __init__(self):
        super().__init__(BYTETracker, "bytetrack.yaml")
