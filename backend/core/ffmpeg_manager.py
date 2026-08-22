import subprocess
import os
from loguru import logger

class FFmpegManager:
    def __init__(self):
        self.processes = {}

    def start_stream(self, camera_id: str, video_path: str) -> str:
        if camera_id in self.processes:
            self.stop_stream(camera_id)
            
        # Output to MediaMTX running on the Mac via Docker
        rtsp_url = f"rtsp://localhost:8554/{camera_id}"
        
        # Stream the video in an infinite loop using native framerate and TCP transport for reliability
        cmd = [
            "ffmpeg", "-re", "-stream_loop", "-1",
            "-i", video_path,
            "-c", "copy",
            "-rtsp_transport", "tcp",
            "-f", "rtsp", rtsp_url
        ]
        
        logger.info(f"Starting FFmpeg stream for {camera_id}: {' '.join(cmd)}")
        # Spawn in new process group so it doesn't get interrupted
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        self.processes[camera_id] = process
        
        return rtsp_url

    def stop_stream(self, camera_id: str):
        if camera_id in self.processes:
            process = self.processes[camera_id]
            logger.info(f"Stopping FFmpeg stream for {camera_id}")
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.processes[camera_id]

ffmpeg_manager = FFmpegManager()
