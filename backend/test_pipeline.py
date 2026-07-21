import time
import queue
import threading
from loguru import logger
from camera.stream_reader import StreamReader
from core.pipeline import InferenceWorker

def test_pipeline():
    logger.info("Testing Inference Pipeline...")
    # Use 0 for webcam or a short video if available
    camera_url = "0" 
    
    result_queue = queue.Queue(maxsize=10)
    
    stream_reader = StreamReader(source=camera_url, buffer_size=3)
    inference_worker = InferenceWorker(
        camera_id=camera_url,
        input_queue=stream_reader.frame_buffer, 
        output_queue=result_queue,
        gesture_queue=None,
        face_worker=None
    )
    
    stream_reader.start()
    inference_worker.start()
    
    frames_processed = 0
    try:
        start_time = time.time()
        while time.time() - start_time < 10: # Run for 10 seconds
            try:
                packet = result_queue.get(timeout=1.0)
                fps = packet.get("fps")
                events = packet.get("events")
                frames_processed += 1
                if frames_processed % 5 == 0:
                    logger.info(f"Processed frame {frames_processed}, FPS: {fps}, Events: {list(events.keys()) if events else 'None'}")
            except queue.Empty:
                pass
    finally:
        logger.info("Stopping workers...")
        inference_worker.stop()
        stream_reader.stop()
        logger.info(f"Test complete. Total frames processed: {frames_processed}")

if __name__ == "__main__":
    test_pipeline()
