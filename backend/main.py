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

# Global FaceWorker instance (can process multiple cameras)
face_worker = FaceWorker()

def start_camera_pipeline(camera_url: str, result_queue: queue.Queue):
    """Initializes and starts the pipeline for a single camera."""
    logger.info(f"Setting up pipeline for {camera_url}")
    
    stream_reader = StreamReader(source=camera_url, buffer_size=config.FRAME_BUFFER_SIZE)
    
    gesture_worker = None
    gesture_queue = None
    if config.GESTURE_ENABLED:
        gesture_queue = queue.Queue(maxsize=10)
        gesture_worker = GestureWorker(
            camera_id=camera_url,
            input_queue=gesture_queue,
            result_queue=result_queue
        )
    
    inference_worker = InferenceWorker(
        camera_id=camera_url,
        input_queue=stream_reader.frame_buffer, 
        output_queue=result_queue,
        gesture_queue=gesture_queue,
        face_worker=face_worker
    )
    
    stream_reader.start()
    if gesture_worker:
        gesture_worker.start()
    inference_worker.start()
    
    return stream_reader, inference_worker, gesture_worker

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
                ignored_redis_events = {None, "info", "PERSON_COUNT", "PARKING_STATS", "QUEUE_STATS", "ATTENDANCE_STATE", "TAMPER_OK", "VISITOR_TRACK"}
                
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
                    
                    redis_client.xadd("logiceye:events", {"data": json.dumps(db_packet)})
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Event loop error: {e}")

def main():
    logger.info("Starting Distributed AI Surveillance Platform Phase 4 (Persistence)...")
    
    result_queue = queue.Queue(maxsize=100)
    
    # 1. Start Database Worker (Now decoupled via Redis)
    db_worker = DatabaseWorker()
    db_worker.start()
    
    # 2. Start Face Worker
    face_worker.start()
    
    # 3. Start Camera Pipelines
    readers = []
    workers = []
    gesture_workers = []
    
    for url in config.camera_list:
        reader, worker, g_worker = start_camera_pipeline(url, result_queue)
        readers.append(reader)
        workers.append(worker)
        if g_worker:
            gesture_workers.append(g_worker)
        
    # 3. Start Event Router (Publishes to Redis)
    threading.Thread(target=event_loop, args=(result_queue,), daemon=True).start()
    
    logger.info("Starting FastAPI web server on port 8000...")
    try:
        # Run Uvicorn in the main thread
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        for w in workers:
            w.stop()
        for gw in gesture_workers:
            gw.stop()
        for r in readers:
            r.stop()
        db_worker.stop()
        face_worker.stop()

if __name__ == "__main__":
    main()
