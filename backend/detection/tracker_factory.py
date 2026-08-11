from detection.interfaces.tracker import ITracker

class DummyTracker(ITracker):
    def update(self, detections, img):
        return detections

class TrackerFactory:
    """
    Factory to instantiate the correct Tracker Strategy based on configuration.
    """
    
    @staticmethod
    def create(tracker_name: str) -> ITracker:
        return DummyTracker()
