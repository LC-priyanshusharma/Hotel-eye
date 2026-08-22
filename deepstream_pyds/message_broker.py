import os
import json
import threading
import redis
from loguru import logger
from gi.repository import GLib

class DeepStreamMessageBroker:
    def __init__(self, add_camera_cb, remove_camera_cb):
        """
        add_camera_cb: Function signature (camera_id: str, rtsp_url: str)
        remove_camera_cb: Function signature (camera_id: str)
        """
        self.add_camera_cb = add_camera_cb
        self.remove_camera_cb = remove_camera_cb
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.r = redis.Redis.from_url(self.redis_url)
        self.pubsub = self.r.pubsub()
        self.channel = "camera_commands"
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.pubsub.subscribe(self.channel)
        self.thread = threading.Thread(target=self._listen_loop, daemon=True, name="RedisSubscriber")
        self.thread.start()
        logger.info(f"DeepStreamMessageBroker listening on Redis channel: {self.channel}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _listen_loop(self):
        while self.running:
            try:
                message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'].decode('utf-8'))
                    self._handle_command(data)
            except Exception as e:
                logger.error(f"Error in DeepStreamMessageBroker loop: {e}")

    def _handle_command(self, data):
        action = data.get("action")
        camera_id = data.get("camera_id")
        
        if not action or not camera_id:
            logger.warning(f"Invalid camera command received: {data}")
            return

        if action == "start":
            rtsp_url = data.get("url")
            if not rtsp_url:
                logger.error("Received start command without RTSP URL.")
                return
            logger.info(f"Received Redis command to ADD camera: {camera_id}")
            # We MUST use GLib.idle_add to safely execute the callback on the main GStreamer thread!
            GLib.idle_add(self.add_camera_cb, camera_id, rtsp_url)
            
        elif action == "stop":
            logger.info(f"Received Redis command to REMOVE camera: {camera_id}")
            GLib.idle_add(self.remove_camera_cb, camera_id)
        else:
            logger.warning(f"Unknown camera action: {action}")
