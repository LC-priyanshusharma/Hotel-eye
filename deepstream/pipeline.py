import os
import sys
import redis
import json
import subprocess
import time
from loguru import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)
pubsub = redis_client.pubsub()
pubsub.subscribe("logiceye:commands")

process = None

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
    
    # Sinks (Redis)
    ds_config += """[sink0]
enable=1
type=6
msg-conv-config=msgconv_config.txt
msg-broker-proto-lib=/opt/nvidia/deepstream/deepstream-6.0/lib/libnvds_redis_proto.so
msg-broker-conn-str=redis;6379;inference_result_ds
topic=inference_result_ds

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

def restart_deepstream(cameras):
    global process
    if process:
        process.terminate()
        process.wait()
    
    if not cameras:
        logger.info("No active cameras. DeepStream stopped.")
        return
        
    generate_config(cameras)
    logger.info("Starting deepstream-app with new configuration...")
    process = subprocess.Popen(["deepstream-app", "-c", "ds_config.txt"])

def main():
    logger.info("DeepStream Manager started. Listening for commands...")
    active_cameras = {}
    
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
                    restart_deepstream(list(active_cameras.values()))
                elif command == "stop_camera":
                    if cam_id in active_cameras:
                        del active_cameras[cam_id]
                        restart_deepstream(list(active_cameras.values()))
                elif command == "sync_cameras":
                    active_cameras = {c["id"]: c for c in data.get("cameras", [])}
                    restart_deepstream(list(active_cameras.values()))
            except Exception as e:
                logger.error(f"Error parsing message: {e}")

if __name__ == "__main__":
    main()
