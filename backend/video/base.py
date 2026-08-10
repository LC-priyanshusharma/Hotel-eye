from abc import ABC, abstractmethod
from typing import Optional, Tuple
import threading
import numpy as np
from dataclasses import dataclass
from enum import Enum

class StreamState(Enum):
    STARTING = "STARTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    OFFLINE = "OFFLINE"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"

@dataclass
class VideoFrame:
    frame: np.ndarray
    capture_time: float
    camera_id: str

@dataclass
class StreamHealth:
    state: StreamState
    fps: float
    reconnect_count: int
    last_seen: float

class VideoSource(ABC):
    """
    Abstract Base Class for all video sources (RTSP, File, GStreamer, etc.).
    """
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        pass

    @abstractmethod
    def grab(self) -> bool:
        pass

    @abstractmethod
    def retrieve(self) -> Tuple[bool, Optional[np.ndarray]]:
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

class VideoPipeline(ABC):
    @abstractmethod
    def start(self) -> None:
        pass
    
    @abstractmethod
    def stop(self) -> None:
        pass
