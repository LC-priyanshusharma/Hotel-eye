from ultralytics.trackers.bot_sort import BOTSORT
from detection.strategies.base_tracker import BaseUltralyticsTrackerStrategy

class BotSortStrategy(BaseUltralyticsTrackerStrategy):
    """
    BoT-SORT implementation of the ITracker interface.
    Uses the underlying Ultralytics BOTSORT for performance.
    """
    def __init__(self):
        super().__init__(BOTSORT, "botsort.yaml")
