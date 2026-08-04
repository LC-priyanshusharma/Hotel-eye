import cv2
import time
import threading
import queue
from typing import Optional, Tuple
from loguru import logger
import numpy as np

from config.config import config
from camera.source import VideoSource

class StreamReader:
    """
    Robust threaded video stream reader using OpenCV.
    
    Reads frames from a video source (RTSP, local file, webcam) in a dedicated
    background thread. cv2.VideoCapture is used for hardware stability across
    macOS, Linux, and Windows.
    """

    def __init__(self, video_source: VideoSource, camera_id: str, buffer_size: int = config.FRAME_BUFFER_SIZE):
        self.source = video_source
        self.camera_id = camera_id
        self.frame_buffer: queue.Queue = queue.Queue(maxsize=buffer_size)
        
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Give source access to the stop event for interruptible reading
        if hasattr(self.source, 'set_stop_event'):
            self.source.set_stop_event(self._stop_event)

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._update, 
            daemon=True, 
            name=f"CV2Reader-{self.camera_id}"
        )
        self._thread.start()
        logger.info(f"Started OpenCV stream reader thread for source: {self.camera_id}")

    def stop(self) -> None:
        self.is_running = False
        self._stop_event.set()
        # Do NOT call self.source.release() here — OpenCV is NOT thread-safe.
        # The thread's finally block will release it safely after exit.
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info(f"Stopped OpenCV stream reader for source: {self.camera_id}")

    def _connect(self) -> bool:
        return self.source.connect()

    def _update(self) -> None:
        backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS

        try:
            while not self._stop_event.is_set():
                if not self.source.is_opened():
                    if not self.source.connect():
                        logger.warning(f"Connection failed for {self.camera_id}. Retrying in {backoff_time}s...")
                        if self._stop_event.wait(backoff_time):
                            break
                        backoff_time = min(backoff_time * 1.5, 30.0)
                        continue
                    backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS
                    self.fps = self.source.fps

                try:
                    # Implement FRAME_SKIP optimization at the decoder level
                    for _ in range(max(1, config.FRAME_SKIP)):
                        if not self.source.grab():
                            break
                    
                    ret, frame = self.source.retrieve()
                    
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from {self.camera_id}. Reconnecting...")
                        self.source.release()
                        if self._stop_event.wait(1.0):
                            break
                        continue
                    
                    # Non-blocking put
                    capture_time = time.time()
                    try:
                        self.frame_buffer.put_nowait((capture_time, frame))
                    except queue.Full:
                        # Drop oldest frame to maintain low latency
                        try:
                            self.frame_buffer.get_nowait()
                            self.frame_buffer.put_nowait((capture_time, frame))
                        except queue.Empty:
                            pass
                            
                except Exception as e:
                    logger.error(f"Exception in stream reader for {self.camera_id}: {e}")
                    self.source.release()
                    if self._stop_event.wait(1.0):
                        break
                    continue
        finally:
            self.source.release()
            
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Used for synchronous pulling if needed, though queues are preferred."""
        try:
            capture_time, frame = self.frame_buffer.get(timeout=0.01)
            return True, frame
        except queue.Empty:
            return False, None
