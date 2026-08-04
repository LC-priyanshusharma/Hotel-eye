import cv2
import time
import threading
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from loguru import logger

class VideoSource(ABC):
    """
    Abstract Base Class for all video sources (RTSP, File, Webcam, etc.).
    """
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[object]]:
        pass

    @abstractmethod
    def grab(self) -> bool:
        """Grabs the next frame without decoding it (useful for frame skipping)."""
        pass

    @abstractmethod
    def retrieve(self) -> Tuple[bool, Optional[object]]:
        """Decodes and returns the grabbed frame."""
        pass

    @abstractmethod
    def release(self) -> None:
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        pass

    def set_stop_event(self, event: threading.Event) -> None:
        pass

    @property
    @abstractmethod
    def fps(self) -> float:
        pass

class OpenCVVideoSource(VideoSource):
    """
    Base implementation using OpenCV for capturing frames.
    """
    def __init__(self, source_path: str):
        self.source_path = source_path.strip('"').strip("'") if isinstance(source_path, str) else source_path
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps = 30.0
        self._stop_event: Optional[threading.Event] = None

    def set_stop_event(self, event: threading.Event) -> None:
        self._stop_event = event
        
    def connect(self) -> bool:
        self.release()
        try:
            # Handle Mac webcam specifically if source is "0"
            if str(self.source_path) == "0":
                import platform
                if platform.system() == "Darwin":
                    self._cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
                else:
                    self._cap = cv2.VideoCapture(0) # Default behavior
            else:
                self._cap = cv2.VideoCapture(self.source_path)
            
            if not self._cap.isOpened():
                raise Exception("VideoCapture not opened")
                
            self._fps = self._cap.get(cv2.CAP_PROP_FPS)
            if self._fps <= 0:
                self._fps = 30.0
                
            # Optional optimizations for RTSP/HTTP streams
            if str(self.source_path).startswith("rtsp://") or str(self.source_path).startswith("http"):
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            
            logger.info(f"Successfully connected to OpenCV source: {self.source_path} @ {self._fps} FPS")
            return True
        except Exception as e:
            logger.error(f"Failed to open source {self.source_path}: {e}")
            self.release()
            return False

    def read(self) -> Tuple[bool, Optional[object]]:
        if self._cap is None:
            return False, None
        return self._cap.read()

    def grab(self) -> bool:
        if self._cap is None:
            return False
        return self._cap.grab()

    def retrieve(self) -> Tuple[bool, Optional[object]]:
        if self._cap is None:
            return False, None
        return self._cap.retrieve()

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def fps(self) -> float:
        return self._fps


class RTSPSource(OpenCVVideoSource):
    """
    Optimized RTSP Source. Relies on base OpenCV features.
    """
    pass


class WebcamSource(OpenCVVideoSource):
    """
    Webcam Source. Relies on base OpenCV features.
    """
    pass


class FileSource(OpenCVVideoSource):
    """
    Local video file source. Maintains original FPS playback to prevent
    fast-forwarding on fast CPUs. Supports looping.
    """
    def __init__(self, source_path: str, loop: bool = True):
        super().__init__(source_path)
        self.loop = loop
        self._frame_delay = 0.033
        
    def connect(self) -> bool:
        success = super().connect()
        if success:
            self._frame_delay = 1.0 / self.fps
        return success

    def grab(self) -> bool:
        if self._cap is None:
            return False
            
        ret = self._cap.grab()
        
        # Handle end of file
        if not ret:
            if self.loop:
                # Small pause after every loop
                if self._stop_event and self._stop_event.wait(2.0):
                    return False
                elif not self._stop_event:
                    time.sleep(2.0)
                # Rewind to start
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret = self._cap.grab()
            else:
                return False
                
        # Simulate real-time playback during grab
        if self._stop_event:
            self._stop_event.wait(self._frame_delay)
        else:
            time.sleep(self._frame_delay)
            
        return ret

    def read(self) -> Tuple[bool, Optional[object]]:
        ret = self.grab()
        if ret:
            return self.retrieve()
        return False, None
