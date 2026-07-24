from detection.interfaces.tracker import ITracker
from detection.strategies.bytetrack import ByteTrackStrategy
from detection.strategies.botsort import BotSortStrategy

class TrackerFactory:
    """
    Factory to instantiate the correct Tracker Strategy based on configuration.
    """
    
    @staticmethod
    def create(tracker_name: str) -> ITracker:
        name = tracker_name.lower().strip()
        if name == "bytetrack":
            return ByteTrackStrategy()
        elif name == "botsort":
            return BotSortStrategy()
        else:
            raise ValueError(f"Unknown tracker configuration: {tracker_name}")
