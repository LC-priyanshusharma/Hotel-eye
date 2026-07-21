import cv2
import time
import threading
import queue
from typing import Optional, Tuple
from loguru import logger
import numpy as np

from config.config import config

class StreamReader:
    """
    Robust threaded video stream reader using OpenCV.
    
    Reads frames from a video source (RTSP, local file, webcam) in a dedicated
    background thread. cv2.VideoCapture is used for hardware stability across
    macOS, Linux, and Windows.
    """

    def __init__(self, source: str, buffer_size: int = config.FRAME_BUFFER_SIZE):
        self.source = source
        self.frame_buffer: queue.Queue = queue.Queue(maxsize=buffer_size)
        
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(
            target=self._update, 
            daemon=True, 
            name=f"CV2Reader-{self.source}"
        )
        self._thread.start()
        logger.info(f"Started OpenCV stream reader thread for source: {self.source}")

    def stop(self) -> None:
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._release_capture()
        logger.info(f"Stopped OpenCV stream reader for source: {self.source}")

    def _release_capture(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _connect(self) -> bool:
        self._release_capture()
        
        try:
            logger.debug(f"Connecting to source: {self.source}...")
            
            # Handle Mac webcam specifically if source is "0"
            if str(self.source) == "0":
                import platform
                if platform.system() == "Darwin":
                    self._cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
                else:
                    self._cap = cv2.VideoCapture(0) # Default behavior
            else:
                self._cap = cv2.VideoCapture(self.source)
            
            if not self._cap.isOpened():
                raise Exception("VideoCapture not opened")
                
            # Optional optimizations for RTSP
            if str(self.source).startswith("rtsp://") or str(self.source).startswith("http"):
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            
            logger.info(f"Successfully connected to OpenCV source: {self.source}")
            return True
        except Exception as e:
            logger.error(f"Failed to open source {self.source}: {e}")
            self._release_capture()
            return False

    def _update(self) -> None:
        backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS

        while self.is_running:
            if self._cap is None or not self._cap.isOpened():
                if not self._connect():
                    logger.warning(f"Connection failed. Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, 30.0)
                    continue
                backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS

            try:
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    logger.warning(f"Failed to grab frame from {self.source}. Reconnecting...")
                    self._release_capture()
                    time.sleep(1.0)
                    continue
                
                if self.frame_buffer.full():
                    try:
                        self.frame_buffer.get_nowait()
                    except queue.Empty:
                        pass
                        
                try:
                    self.frame_buffer.put_nowait(frame)
                except queue.Full:
                    pass
                    
            except Exception as e:
                logger.error(f"Unexpected error in capture thread: {e}")
                self._release_capture()
                time.sleep(1.0)
                continue
            
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Used for synchronous pulling if needed, though queues are preferred."""
        try:
            frame = self.frame_buffer.get(timeout=0.01)
            return True, frame
        except queue.Empty:
            return False, None
