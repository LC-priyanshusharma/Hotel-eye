import uvicorn
import threading
import queue
import time
from loguru import logger
import os

from config.config import config
from core.events.bus import RedisEventBus
from api.server import app  # Required for uvicorn main:app

def ds_consumer(result_queue: queue.Queue):
    """Listens to DeepStream inference results via Redis."""
    import redis
    import json
    from core.pipeline import DetectionEngine
    from app.engine.base import FrameData
    
    logger.info("Started DeepStream consumer loop.")
    redis_client = redis.Redis.from_url(config.REDIS_URL)
    pubsub = redis_client.pubsub()
    pubsub.subscribe("inference_result_ds")
    
    engine = DetectionEngine()
    
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                # DeepStream minimal JSON parse
                ds_data = json.loads(message["data"])
                
                # NvMsgConv format varies, let's assume it provides objects
                # We extract bounding boxes and feed into our DetectionEngine
                # This logic translates DeepStream JSON into LogicEye's expected format
                camera_id = ds_data.get("sensor", {}).get("id", "camera1")
                
                objects = ds_data.get("object", [])
                
                from app.engine.base import NormalizedDetection
                
                detections = []
                for obj in objects:
                    bbox = obj.get("bbox", {})
                    x = bbox.get("left", 0.0)
                    y = bbox.get("top", 0.0)
                    w = bbox.get("width", 0.0)
                    h = bbox.get("height", 0.0)
                    
                    # NvTracker outputs object_id when tracking is enabled
                    track_id = obj.get("object_id")
                    
                    # class_id is typically provided by nvmsgconv
                    cls_id = obj.get("class_id", 0) 
                    conf = obj.get("confidence", 1.0)
                    
                    det = NormalizedDetection(
                        class_id=int(cls_id),
                        confidence=float(conf),
                        bbox=[float(x), float(y), float(x+w), float(y+h)],
                        track_id=int(track_id) if track_id is not None else None
                    )
                    detections.append(det)
                
                frame_data = FrameData(
                    frame=None, # No frame available from DeepStream over Redis natively
                    detections=detections,
                    camera_id=camera_id,
                    timestamp=time.time(),
                    faces=[],
                    camera_url=camera_id
                )
                
                events = engine.run_plugins(frame_data)
                
                packet = {
                    "camera_id": camera_id,
                    "frame": None,
                    "detections": detections,
                    "events": events,
                    "fps": 30.0,
                    "latency_ms": 0,
                    "timestamp": time.time()
                }
                
                if result_queue.full():
                    try:
                        result_queue.get_nowait()
                    except queue.Empty:
                        pass
                result_queue.put_nowait(packet)
            except Exception as e:
                logger.error(f"Error parsing DeepStream message: {e}")

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
                    logger.debug(f"Published event packet to Redis for camera {packet['camera_id']}")
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Event loop error: {e}")

def telemetry_consumer():
    """Listens to Edge Telemetry via Redis and caches it."""
    import redis
    import json
    from config.config import config
    from core.telemetry_cache import telemetry_cache
    
    logger.info("Started Telemetry consumer loop.")
    try:
        redis_client = redis.Redis.from_url(config.REDIS_URL)
        pubsub = redis_client.pubsub()
        pubsub.subscribe("logiceye:telemetry")
        
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    edge_id = data.get("edge_id", "unknown")
                    telemetry_cache.update(edge_id, data)
                except Exception as e:
                    logger.error(f"Error parsing telemetry message: {e}")
    except Exception as e:
        logger.error(f"Telemetry consumer failed: {e}")

def main():
    """Entry point — all initialization is handled by server.py startup event."""
    logger.info("Starting LogicEye AI CCTV Platform...")
    try:
        threading.Thread(target=telemetry_consumer, daemon=True).start()
        uvicorn.run("api.server:app", host="0.0.0.0", port=8000, log_level="error")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Force an immediate clean exit to bypass macOS native library (OpenCV/Paddle/CoreAudio) destructor segfaults
        import os
        os._exit(0)

if __name__ == "__main__":
    main()
