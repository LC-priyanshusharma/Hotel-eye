import av
import time
import threading
import queue
from typing import Optional, Tuple
from loguru import logger
import numpy as np

from core.config import config

class StreamReader:
    """
    Robust threaded video stream reader using PyAV.
    
    Reads frames from a video source (RTSP, local file, webcam) in a dedicated
    background thread. PyAV is used for superior FFmpeg buffer control,
    preventing the infamous latency drift common with OpenCV.
    """

    def __init__(self, source: str, buffer_size: int = config.FRAME_BUFFER_SIZE):
        self.source = source
        self.frame_buffer: queue.Queue = queue.Queue(maxsize=buffer_size)
        
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._container: Optional[av.container.InputContainer] = None

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(
            target=self._update, 
            daemon=True, 
            name=f"PyAVReader-{self.source}"
        )
        self._thread.start()
        logger.info(f"Started PyAV stream reader thread for source: {self.source}")

    def stop(self) -> None:
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._release_capture()
        logger.info(f"Stopped PyAV stream reader for source: {self.source}")

    def _release_capture(self) -> None:
        if self._container is not None:
            self._container.close()
            self._container = None

    def _connect(self) -> bool:
        self._release_capture()
        
        # Determine format options for low latency
        options = {}
        if str(self.source).startswith("rtsp://") or str(self.source).startswith("http"):
            options = {
                "rtsp_transport": "tcp",
                "fflags": "nobuffer",
                "flags": "low_delay",
                "strict": "experimental"
            }
            
        try:
            logger.debug(f"Connecting to source: {self.source}...")
            
            # Handle Mac webcam specifically if source is "0"
            if str(self.source) == "0":
                import platform
                if platform.system() == "Darwin":
                    self._container = av.open(
                        "default", format="avfoundation", options={"framerate": "30", "pixel_format": "yuyv422"}
                    )
                else:
                    self._container = av.open(self.source) # Default behavior
            else:
                self._container = av.open(self.source, options=options, timeout=5.0)
            
            logger.info(f"Successfully connected to PyAV source: {self.source}")
            return True
        except Exception as e:
            logger.error(f"Failed to open source {self.source}: {e}")
            self._release_capture()
            return False

    def _update(self) -> None:
        backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS

        while self.is_running:
            if self._container is None:
                if not self._connect():
                    logger.warning(f"Connection failed. Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 1.5, 30.0)
                    continue
                backoff_time = config.CAMERA_RECONNECT_DELAY_SECONDS

            try:
                # We decode only the video stream
                stream = self._container.streams.video[0]
                stream.thread_type = 'AUTO' # Enable multithreaded decoding
                
                for frame in self._container.decode(stream):
                    if not self.is_running:
                        break
                        
                    # Convert PyAV VideoFrame to numpy array (BGR for OpenCV compatibility)
                    img_np = frame.to_ndarray(format='bgr24')
                    
                    if self.frame_buffer.full():
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            pass
                            
                    try:
                        self.frame_buffer.put_nowait(img_np)
                    except queue.Full:
                        pass
                        
            except Exception as e:
                logger.error(f"Unexpected error in capture thread: {e}")
                self._release_capture()
                time.sleep(1.0)
                continue
            
            if self.is_running:
                logger.info(f"End of stream {self.source}. Reconnecting...")
                self._release_capture()
                time.sleep(1.0)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Used for synchronous pulling if needed, though queues are preferred."""
        try:
            frame = self.frame_buffer.get(timeout=0.01)
            return True, frame
        except queue.Empty:
            return False, None
