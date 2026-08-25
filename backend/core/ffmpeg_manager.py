import subprocess
import os
import time
from loguru import logger

class FFmpegManager:
    def __init__(self):
        self.processes = {}

    def resolve_video_path(self, video_path: str) -> str:
        """Resolves absolute path or paths relative to workspace or videos folder."""
        if not video_path:
            return ""
        if video_path.startswith("rtsp://") or video_path.startswith("http://") or video_path.startswith("https://"):
            return video_path
        if video_path.startswith("file://"):
            video_path = video_path[7:]
            
        if os.path.isabs(video_path) and os.path.exists(video_path):
            return video_path
            
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            video_path,
            os.path.join(base_dir, "videos", os.path.basename(video_path)),
            os.path.join(os.path.dirname(base_dir), "videos", os.path.basename(video_path)),
            os.path.join(base_dir, video_path),
            os.path.join(os.path.dirname(base_dir), video_path)
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return video_path

    def start_stream(self, camera_id: str, video_path: str) -> str:
        if camera_id in self.processes:
            self.stop_stream(camera_id)
            
        resolved_path = self.resolve_video_path(video_path)
        raw_rtsp_url = f"rtsp://localhost:8554/raw_{camera_id}"
        
        is_rtsp = resolved_path.startswith("rtsp://") or resolved_path.startswith("rtsps://")
        if not is_rtsp and not os.path.exists(resolved_path):
            logger.warning(f"Video file not found at '{video_path}' (resolved: '{resolved_path}')")
            return video_path
            
        if is_rtsp:
            # RTSP to MediaMTX relay with auto-reconnect
            cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", resolved_path,
                "-c:v", "copy",
                "-an",
                "-f", "rtsp",
                "-rtsp_transport", "tcp",
                raw_rtsp_url
            ]
        else:
            # Video file loop
            cmd = [
                "ffmpeg", "-re", "-stream_loop", "-1",
                "-i", resolved_path,
                "-c:v", "copy",
                "-an",
                "-rtsp_transport", "tcp",
                "-f", "rtsp", raw_rtsp_url
            ]
        
        logger.info(f"Starting stream for camera {camera_id}")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self.processes[camera_id] = process
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to spawn FFmpeg for {camera_id}: {e}")
            
        return raw_rtsp_url

    def stop_stream(self, camera_id: str):
        if camera_id in self.processes:
            process = self.processes[camera_id]
            logger.info(f"Stopping FFmpeg stream for {camera_id}")
            try:
                process.terminate()
                process.wait(timeout=1.5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            del self.processes[camera_id]

ffmpeg_manager = FFmpegManager()
