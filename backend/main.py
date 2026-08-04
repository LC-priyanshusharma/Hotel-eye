import uvicorn
import threading
import queue
import time
from loguru import logger
import os

from config.config import config
from core.events.bus import RedisEventBus
from api.server import app  # Required for uvicorn main:app

def event_loop(result_queue: queue.Queue):
    """Pulls results from all cameras, updates API state, and forwards actionable events to Redis."""
    from core.state import update_global_state
    from fastapi.encoders import jsonable_encoder
    import json
    logger.info("Started global event loop (Redis Publisher).")
    
    # Single RedisEventBus instance — avoid creating a new connection per event
    event_bus = RedisEventBus(config.REDIS_URL)
    
    while True:
        try:
            packet = result_queue.get(timeout=1.0)
            
            # 1. Update API state
            update_global_state(packet)
            
            # 2. Forward to Database worker via Redis
            # We only send metadata (events) over Redis to avoid massive memory/network bloat
            if packet.get("events"):
                ignored_redis_events = {None, "info", "PERSON_COUNT", "PARKING_STATS", "ATTENDANCE_STATE", "VISITOR_TRACK", "CARTON_TRACK", "CARTON_STATS", "ANPR_STATS", "LIVE_TRACKING"}
                
                filtered_events = {}
                for plugin_name, plugin_events in packet["events"].items():
                    if isinstance(plugin_events, list):
                        valid_plugin_events = []
                        for e in plugin_events:
                            e_type = getattr(e, "event_type", None)
                            if e_type is None and isinstance(e, dict):
                                e_type = e.get("event_type")
                            if e_type not in ignored_redis_events:
                                # Convert to dict if it's an object so json.dumps works flawlessly
                                e_dict = e if isinstance(e, dict) else (e.dict() if hasattr(e, "dict") else e.__dict__)
                                valid_plugin_events.append(e_dict)
                        if valid_plugin_events:
                            filtered_events[plugin_name] = valid_plugin_events
                        
                if filtered_events:
                    from core.utils import clean_numpy
                    cleaned_events = clean_numpy(filtered_events)
                    db_packet = jsonable_encoder({
                        "camera_id": packet["camera_id"],
                        "timestamp": packet["timestamp"],
                        "events": cleaned_events
                    })
                    
                    event_bus.publish("logiceye:events", db_packet)
                    logger.info(f"Published event packet to Redis for camera {packet['camera_id']}")
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Event loop error: {e}")

def main():
    """Entry point — all initialization is handled by server.py startup event."""
    logger.info("Starting LogicEye AI CCTV Platform...")
    try:
        uvicorn.run("api.server:app", host="0.0.0.0", port=8000, log_level="error")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Force an immediate clean exit to bypass macOS native library (OpenCV/Paddle/CoreAudio) destructor segfaults
        import os
        os._exit(0)

if __name__ == "__main__":
    main()
