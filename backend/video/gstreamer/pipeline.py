import subprocess
import threading
import time
import numpy as np
from typing import Optional, Tuple
from loguru import logger
from video.base import VideoSource

class GStreamerSource(VideoSource):
    """
    Production-grade GStreamer RTSP ingestion pipeline via Subprocess & Pipe.
    This completely bypasses Python's OpenCV/PyGObject compilation limitations on Mac/Windows
    by running the native C binary directly and piping the frames as bytes.
    """
    def __init__(self, source_path: str, camera_id: str):
        self.source_path = source_path.strip('"').strip("'")
        self.camera_id = camera_id
        self._fps = 30.0
        self._stop_event: Optional[threading.Event] = None
        
        self.proc = None
        self.latest_frame = None
        self.lock = threading.Lock()
        
        # Standardize internal resolution for byte-exact pipe extraction
        self.width = 1280
        self.height = 720
        self.frame_size = self.width * self.height * 3
        
        self.reader_thread = None
        self._running = False

    def _build_command(self) -> list:
        # Check if it's a network stream or local file
        is_network = self.source_path.startswith("rtsp://") or self.source_path.startswith("rtmp://") or self.source_path.startswith("http")
        
        if is_network:
            input_pipe = f"rtspsrc location={self.source_path} latency=100 drop-on-latency=true ! rtph264depay ! h264parse ! decodebin"
        else:
            # Handle local file ingestion natively
            input_pipe = f"uridecodebin uri=file://{self.source_path}"

        return [
            "gst-launch-1.0", "-q",
            *input_pipe.split(" "), "!",
            "videoconvert", "!", "videoscale", "!", 
            f"video/x-raw,format=BGR,width={self.width},height={self.height}", "!",
            "fdsink", "fd=1", "sync=false"
        ]

    def _reader_loop(self):
        while self._running and self.proc and self.proc.stdout:
            try:
                # Read exactly one 1280x720 frame from the binary pipe
                raw = self.proc.stdout.read(self.frame_size)
                if not raw or len(raw) < self.frame_size:
                    logger.warning(f"[{self.camera_id}] GStreamer Pipe closed or EOF")
                    break
                
                # Convert raw bytes instantly to a NumPy array (Zero copy overhead compared to MJPEG!)
                frame = np.frombuffer(raw, dtype=np.uint8).reshape((self.height, self.width, 3))
                with self.lock:
                    self.latest_frame = frame
            except Exception as e:
                logger.error(f"[{self.camera_id}] GStreamer Pipe error: {e}")
                break
                
        self.release()

    def set_stop_event(self, event: threading.Event) -> None:
        self._stop_event = event

    def connect(self) -> bool:
        self.release()
        try:
            cmd = self._build_command()
            logger.info(f"[{self.camera_id}] Launching GStreamer Universal Subprocess Pipeline...")
            
            # Start native gst-launch-1.0 binary
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            self._running = True
            self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.reader_thread.start()
            
            # Wait for first frame to ensure connection is actually established
            for _ in range(50):
                if self.grab():
                    logger.info(f"[{self.camera_id}] Native GStreamer Pipeline Connected!")
                    return True
                time.sleep(0.1)
                
            raise Exception("Timeout waiting for first GStreamer frame")
        except Exception as e:
            logger.error(f"[{self.camera_id}] GStreamer connection failed: {e}")
            self.release()
            return False

    def grab(self) -> bool:
        with self.lock:
            return self.latest_frame is not None

    def retrieve(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.latest_frame is not None:
                return True, self.latest_frame
            return False, None

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.latest_frame is not None:
                return True, self.latest_frame
            return False, None

    def release(self) -> None:
        self._running = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except:
                    pass
            self.proc = None
            
        self.latest_frame = None

    def is_opened(self) -> bool:
        return self._running and self.proc is not None and self.proc.poll() is None

    @property
    def fps(self) -> float:
        return self._fps
