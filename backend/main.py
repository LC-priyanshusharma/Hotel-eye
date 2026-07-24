import uvicorn
import threading
import queue
import time
from loguru import logger
import os

from config.config import config
from camera.stream_reader import StreamReader
from core.pipeline import InferenceWorker
from database.persistence import DatabaseWorker
from api.server import app, update_global_state
from tracking.gesture import GestureWorker
from face.worker import FaceWorker

from core.camera_manager import camera_manager

def event_loop(result_queue: queue.Queue):
    """Pulls results from all cameras, updates API state, and forwards actionable events to Redis."""
    from config.config import redis_client
    import json
    logger.info("Started global event loop (Redis Publisher).")
    while True:
        try:
            packet = result_queue.get(timeout=1.0)
            
            # 1. Update API state
            update_global_state(packet)
            
            # 2. Forward to Database worker via Redis
            # We only send metadata (events) over Redis to avoid massive memory/network bloat
            if packet.get("events"):
                ignored_redis_events = {None, "info", "PERSON_COUNT", "PARKING_STATS", "ATTENDANCE_STATE", "VISITOR_TRACK"}
                
                filtered_events = []
                for e in packet["events"]:
                    e_type = getattr(e, "event_type", None)
                    if e_type is None and isinstance(e, dict):
                        e_type = e.get("event_type")
                        
                    if e_type not in ignored_redis_events:
                        # Convert to dict if it's an object so json.dumps works flawlessly
                        e_dict = e if isinstance(e, dict) else (e.dict() if hasattr(e, "dict") else e.__dict__)
                        filtered_events.append(e_dict)
                        
                if filtered_events:
                    db_packet = {
                        "camera_id": packet["camera_id"],
                        "timestamp": packet["timestamp"],
                        "events": filtered_events
                    }
                    
                    from core.events.bus import RedisEventBus
                    event_bus = RedisEventBus(config.REDIS_URL)
                    event_bus.publish("logiceye:events", db_packet)
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Event loop error: {e}")

def main():
    logger.info("Starting Distributed AI Surveillance Platform Phase 4 (Persistence)...")
    
    # 1. Start Database Worker (Now decoupled via Redis)
    db_worker = DatabaseWorker()
    db_worker.start()
    
    # 2. Start Global Workers
    camera_manager.start_global_workers()
    
    # 3. Start Camera Pipelines
    from database.session import SessionLocal
    from models.models import Camera
    db = SessionLocal()
    try:
        saved_cameras = db.query(Camera).filter(Camera.active == True).all()
        logger.info(f"Loaded {len(saved_cameras)} active cameras from database.")
        for cam in saved_cameras:
            if cam.rtsp_url not in config.camera_list:
                config.camera_list.append(cam.rtsp_url)
            camera_manager.start_camera_pipeline(cam.rtsp_url)
            
        # Fallback to env vars if DB is completely empty (first boot)
        if not saved_cameras:
            for url in config.camera_list:
                camera_manager.start_camera_pipeline(url)
    except Exception as e:
        logger.error(f"Failed to load cameras from DB: {e}")
        for url in config.camera_list:
            camera_manager.start_camera_pipeline(url)
    finally:
        db.close()
        
    # 4. Start Event Router (Publishes to Redis)
    threading.Thread(target=event_loop, args=(camera_manager.result_queue,), daemon=True).start()
    
    logger.info("Starting FastAPI web server on port 8000...")
    try:
        # Run Uvicorn in the main thread
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        camera_manager.stop_all()
        db_worker.stop()

if __name__ == "__main__":
    main()
