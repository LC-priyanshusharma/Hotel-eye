import queue
from datetime import datetime
from database.persistence import DatabaseWorker

def test_is_actionable():
    q = queue.Queue()
    worker = DatabaseWorker(result_queue=q)
    
    # 1. Actionable event (has active alerts)
    event1 = {
        "PluginA": [{
            "event_type": "object_detected",
            "active_alerts": ["Intrusion Alert"],
            "detections": 5
        }]
    }
    assert worker._is_actionable(event1) == True

    # 2. Actionable event (attendance specific)
    event2 = {
        "AttendancePlugin": [{
            "event_type": "attendance_check_in",
            "active_alerts": [],
            "person_id": 123
        }]
    }
    assert worker._is_actionable(event2) == True

    # 3. Spam event (just background detection)
    event3 = {
        "PluginA": [{
            "event_type": "info",
            "active_alerts": [],
            "detections": 5
        }]
    }
    assert worker._is_actionable(event3) == False
