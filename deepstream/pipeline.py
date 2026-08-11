import os
import sys
import redis
import json
import subprocess
import time
import threading
from loguru import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)
pubsub = redis_client.pubsub()
pubsub.subscribe("logiceye:commands")

process = None
active_cameras = {}
restart_lock = threading.Lock()
restart_timer = None

def generate_config(cameras):
    # Base DS Config
    ds_config = """[application]
enable-perf-measurement=1
perf-measurement-interval-sec=5

[tiled-display]
enable=0

"""
    # Sources
    for i, cam in enumerate(cameras):
        ds_config += f"""[source{i}]
enable=1
type=4
uri={cam['url']}
num-sources=1
gpu-id=0

"""
    
    # Sinks (fakesink — we do NOT use the DS message broker; 
    # MediaMTX handles the video streaming to dashboard)
    ds_config += """[sink0]
enable=1
type=1

[osd]
enable=0

[streammux]
gpu-id=0
live-source=1
batch-size=1
batched-push-timeout=40000
width=1280
height=720

[primary-gie]
enable=1
gpu-id=0
batch-size=1
interval=0
gie-unique-id=1
config-file=config_infer_yolo.txt
"""
    with open("ds_config.txt", "w") as f:
        f.write(ds_config)

def _do_restart():
    """Actually perform the restart. Called after debounce delay."""
    global process
    with restart_lock:
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process = None
        
        cameras = list(active_cameras.values())
        if not cameras:
            logger.info("No active cameras. DeepStream stopped.")
            return
            
        generate_config(cameras)
        logger.info(f"Starting deepstream-app with {len(cameras)} camera(s)...")
        process = subprocess.Popen(["deepstream-app", "-c", "ds_config.txt"])

def schedule_restart():
    """Debounce restarts — wait 2 seconds for all camera commands to arrive before restarting."""
    global restart_timer
    if restart_timer:
        restart_timer.cancel()
    restart_timer = threading.Timer(2.0, _do_restart)
    restart_timer.start()

def main():
    logger.info("DeepStream Manager started. Listening for commands...")
    
    # Send a ready ping to backend so it knows to sync active cameras
    redis_client.publish("logiceye:ds_status", "ready")
    
    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            try:
                data = json.loads(message["data"])
                command = data.get("command")
                cam_id = data.get("camera_id")
                url = data.get("url")
                
                if command == "start_camera":
                    active_cameras[cam_id] = {"url": url}
                    logger.info(f"Queued camera {cam_id} for start. Total: {len(active_cameras)}")
                    schedule_restart()
                elif command == "stop_camera":
                    if cam_id in active_cameras:
                        del active_cameras[cam_id]
                        logger.info(f"Removed camera {cam_id}. Total: {len(active_cameras)}")
                        schedule_restart()
                elif command == "sync_cameras":
                    active_cameras.clear()
                    for c in data.get("cameras", []):
                        active_cameras[c["id"]] = c
                    logger.info(f"Synced {len(active_cameras)} cameras.")
                    schedule_restart()
            except Exception as e:
                logger.error(f"Error parsing message: {e}")

if __name__ == "__main__":
    main()
