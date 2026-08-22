import os
import sys
import redis
import json
import subprocess
import time
import threading
from urllib.parse import urlparse, quote, urlunparse
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
try:
    from jtop import jtop
    HAS_JTOP = True
except ImportError:
    HAS_JTOP = False
from typing import Dict, List
from loguru import logger

from engine_manager import EngineManager

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EDGE_ID = os.getenv("EDGE_ID", "edge-01")
MAX_CAMERAS_PER_WORKER = int(os.getenv("MAX_CAMERAS_PER_WORKER", "4"))
ONNX_PATH = os.getenv("ONNX_PATH", "/app/backend/detection/yolo11n_opset12.onnx")
ENGINE_PATH = os.getenv("ENGINE_PATH", f"/app/backend/detection/yolo11n_opset12.onnx_b{MAX_CAMERAS_PER_WORKER}_gpu0_fp16.engine")
CONFIG_INFER_PATH = os.getenv("CONFIG_INFER_PATH", "config_infer_yolo.txt")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
pubsub = redis_client.pubsub()
pubsub.subscribe("logiceye:commands")

class WorkerProcess:
    def __init__(self, worker_id: int, cameras: List[Dict]):
        self.worker_id = worker_id
        self.cameras = cameras
        self.process = None
        self.config_path = f"ds_config_worker_{worker_id}.txt"
    
    @staticmethod
    def encode_rtsp_url(url: str) -> str:
        """Properly encode special characters in RTSP URL credentials.
        Handles passwords containing @, #, ?, etc. by URL-encoding them."""
        if not url or '://' not in url:
            return url
        try:
            parsed = urlparse(url)
            if parsed.password and any(c in parsed.password for c in '@#?&'):
                encoded_pw = quote(parsed.password, safe='')
                # Reconstruct: scheme://user:encoded_pw@host:port/path
                netloc = f"{parsed.username}:{encoded_pw}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        except Exception:
            pass
        return url
        
    def generate_config(self):
        ds_config = f"""[application]
enable-perf-measurement=1
perf-measurement-interval-sec=5

[tiled-display]
enable=0

"""
        for i, cam in enumerate(self.cameras):
            encoded_url = self.encode_rtsp_url(cam['url'])
            ds_config += f"""[source{i}]
enable=1
type=4
uri={encoded_url}
num-sources=1
gpu-id=0

"""
        # Add an OSD and RTSP sink for EACH camera
        for i, cam in enumerate(self.cameras):
            base_port = 8555 + (self.worker_id * 10) + i
            udp_port = 5400 + (self.worker_id * 10) + i
            # In deepstream-app, to output separate streams without tiling, we use link-to-source-id
            ds_config += f"""[sink{i}]
enable=1
type=4
codec=1
bitrate=2000000
rtsp-port={base_port}
udp-port={udp_port}
iframeinterval=30
"""
            if len(self.cameras) > 1:
                ds_config += f"link-to-source-id={i}\n"
            ds_config += "\n"

        ds_config += f"""[osd]
enable=1

[streammux]
gpu-id=0
live-source=1
batch-size={len(self.cameras)}
batched-push-timeout=40000
width=1280
height=720

[primary-gie]
enable=1
gpu-id=0
batch-size={len(self.cameras)}
interval=0
gie-unique-id=1
config-file={CONFIG_INFER_PATH}
"""
        with open(self.config_path, "w") as f:
            f.write(ds_config)

    def start(self):
        self.generate_config()
        logger.info(f"[Worker {self.worker_id}] Starting with {len(self.cameras)} cameras. Batch size: {len(self.cameras)}")
        # Start the reference app
        self.process = subprocess.Popen(["deepstream-app", "-c", self.config_path])
        
        time.sleep(3) # Wait for DeepStream RTSP servers to start
        
        # Tell MediaMTX to pull from DeepStream internal RTSP servers
        for i, cam in enumerate(self.cameras):
            cam_id = cam["id"]
            base_port = 8555 + (self.worker_id * 10) + i
            # Using the MediaMTX API to add the path dynamically
            # deepstream container hostname is deepstream
            url = f"http://mediamtx:9997/v3/config/paths/add/{cam_id}"
            payload = {
                "source": f"rtsp://deepstream:{base_port}/ds-test",
                "sourceOnDemand": False
            }
            try:
                requests.post(url, json=payload, timeout=5)
                logger.info(f"Configured MediaMTX to pull {cam_id} from deepstream:{base_port}")
            except Exception as e:
                logger.error(f"Failed to configure MediaMTX for {cam_id}: {e}")
        
    def stop(self):
        for cam in self.cameras:
            try:
                requests.post(f"http://mediamtx:9997/v3/config/paths/remove/{cam['id']}", timeout=5)
                logger.info(f"Removed {cam['id']} from MediaMTX")
            except Exception as e:
                logger.error(f"Failed to remove {cam['id']} from MediaMTX: {e}")
                
        if self.process:
            logger.info(f"[Worker {self.worker_id}] Stopping...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None


class WorkerPoolManager:
    def __init__(self):
        self.workers: Dict[int, WorkerProcess] = {}
        self.camera_to_worker: Dict[str, int] = {}
        self.next_worker_id = 1
        
        self.pending_cameras: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.batch_timer = None
        
    def _spawn_pending_workers(self):
        """Spawns new workers for pending cameras in chunks of MAX_CAMERAS_PER_WORKER."""
        with self.lock:
            if not self.pending_cameras:
                return
                
            camera_items = list(self.pending_cameras.items())
            self.pending_cameras.clear()
            
            # Chunk them into sizes of MAX_CAMERAS_PER_WORKER
            for i in range(0, len(camera_items), MAX_CAMERAS_PER_WORKER):
                chunk = camera_items[i:i + MAX_CAMERAS_PER_WORKER]
                cam_dicts = [{"id": cid, "url": url} for cid, url in chunk]
                
                w_id = self.next_worker_id
                self.next_worker_id += 1
                
                worker = WorkerProcess(w_id, cam_dicts)
                self.workers[w_id] = worker
                
                for cid, _ in chunk:
                    self.camera_to_worker[cid] = w_id
                    
                if HAS_JTOP:
                    try:
                        with jtop() as jetson:
                            if jetson.ok():
                                v_before = jetson.memory.get('RAM', {}).get('used', 0)
                                logger.info(f"VRAM before Worker {w_id} spawn: {v_before}MB")
                                worker.start()
                                time.sleep(3) # Wait for engine to load into VRAM
                                v_after = jetson.memory.get('RAM', {}).get('used', 0)
                                diff = v_after - v_before
                                logger.info(f"VRAM after Worker {w_id} spawn: {v_after}MB (Cost: +{diff}MB)")
                            else:
                                worker.start()
                    except Exception as e:
                        logger.error(f"Error measuring VRAM: {e}")
                        worker.start()
                else:
                    worker.start()
                
            self.batch_timer = None

    def add_camera(self, cam_id: str, url: str):
        with self.lock:
            if cam_id in self.camera_to_worker:
                logger.info(f"Camera {cam_id} is already running in Worker {self.camera_to_worker[cam_id]}")
                return
                
            self.pending_cameras[cam_id] = url
            logger.info(f"Queued camera {cam_id} for new worker batch.")
            
            if self.batch_timer:
                self.batch_timer.cancel()
                
            # Wait 2 seconds to batch multiple requests together into one worker
            self.batch_timer = threading.Timer(2.0, self._spawn_pending_workers)
            self.batch_timer.start()

    def remove_camera(self, cam_id: str):
        with self.lock:
            if cam_id in self.pending_cameras:
                del self.pending_cameras[cam_id]
                return
                
            if cam_id in self.camera_to_worker:
                w_id = self.camera_to_worker[cam_id]
                worker = self.workers[w_id]
                logger.info(f"Removing camera {cam_id} from Worker {w_id}")
                
                # To remove a camera from a worker without dynamic sources, we MUST restart that worker.
                # On REMOVE, we can either:
                # 1. Stop the whole worker, remove the camera, and spawn a new worker for the remaining ones.
                # 2. Just let the stream timeout in DeepStream (failing gracefully).
                # To be clean and save resources, we will recreate the worker with the remaining cameras.
                worker.stop()
                
                remaining_cams = [c for c in worker.cameras if c["id"] != cam_id]
                del self.workers[w_id]
                del self.camera_to_worker[cam_id]
                
                for c in remaining_cams:
                    del self.camera_to_worker[c["id"]]
                    self.add_camera(c["id"], c["url"])

    def sync_cameras(self, target_cameras: List[Dict]):
        """Compares target state to current state and adds/removes as necessary."""
        target_ids = {c["id"] for c in target_cameras}
        current_ids = set(self.camera_to_worker.keys()).union(set(self.pending_cameras.keys()))
        
        to_add = [c for c in target_cameras if c["id"] not in current_ids]
        to_remove = current_ids - target_ids
        
        for c in to_add:
            self.add_camera(c["id"], c["url"])
            
        for cid in to_remove:
            self.remove_camera(cid)

    def supervise_workers(self):
        """Checks for crashed workers and restarts them."""
        with self.lock:
            crashed_workers = []
            for w_id, worker in self.workers.items():
                if not worker.is_running():
                    logger.error(f"[Worker {w_id}] Crashed! Scheduling restart...")
                    crashed_workers.append(w_id)
            
            for w_id in crashed_workers:
                worker = self.workers[w_id]
                del self.workers[w_id]
                for cam in worker.cameras:
                    del self.camera_to_worker[cam["id"]]
                    self.add_camera(cam["id"], cam["url"])

def main():
    logger.info(f"Starting LogicEye Edge Worker Manager (EDGE_ID: {EDGE_ID})")
    
    # Phase 1: Ensure Engine is built ONCE before touching any cameras
    engine_manager = EngineManager(ONNX_PATH, ENGINE_PATH)
    if not engine_manager.ensure_engine_ready(CONFIG_INFER_PATH):
        logger.critical("Failed to build or validate TensorRT engine. Exiting.")
        sys.exit(1)
        
    pool = WorkerPoolManager()
    
    # Notify backend we are ready for assignments
    redis_client.publish("logiceye:ds_status", json.dumps({"edge_id": EDGE_ID, "status": "ready"}))
    
    # Supervisor loop runs in background
    def supervisor():
        while True:
            time.sleep(10)
            pool.supervise_workers()
            
    threading.Thread(target=supervisor, daemon=True).start()
    
    # Telemetry loop runs in background
    def telemetry_supervisor():
        if HAS_JTOP:
            try:
                with jtop() as jetson:
                    while True:
                        if jetson.ok():
                            cpus = list(jetson.cpu.values())
                            cpu_avg = sum([c.get('val', 0) for c in cpus]) / max(len(cpus), 1)
                            payload = {
                                "edge_id": EDGE_ID,
                                "gpu_load": jetson.gpu.get('val', 0),
                                "cpu_load": cpu_avg,
                                "ram_used": jetson.memory.get('RAM', {}).get('used', 0),
                                "ram_total": jetson.memory.get('RAM', {}).get('tot', 0),
                                "temp": jetson.temperature.get('GPU', {}).get('temp', 0),
                                "active_workers": len(pool.workers),
                                "timestamp": time.time()
                            }
                            redis_client.publish("logiceye:telemetry", json.dumps(payload))
                        time.sleep(5)
            except Exception as e:
                logger.error(f"jtop telemetry failed: {e}")
        
        # Fallback if jtop fails or is missing
        while True:
            payload = {
                "edge_id": EDGE_ID,
                "gpu_load": 0,
                "cpu_load": psutil.cpu_percent() if HAS_PSUTIL else 0,
                "ram_used": (psutil.virtual_memory().used / (1024*1024)) if HAS_PSUTIL else 0,
                "ram_total": (psutil.virtual_memory().total / (1024*1024)) if HAS_PSUTIL else 0,
                "temp": 0,
                "active_workers": len(pool.workers),
                "timestamp": time.time()
            }
            redis_client.publish("logiceye:telemetry", json.dumps(payload))
            time.sleep(5)
            
    threading.Thread(target=telemetry_supervisor, daemon=True).start()
    
    # Listen to Redis commands
    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            try:
                data = json.loads(message["data"])
                target_edge = data.get("edge_id", EDGE_ID)
                
                # Ignore commands not meant for this edge device
                if target_edge != EDGE_ID:
                    continue
                    
                command = data.get("command")
                cam_id = data.get("camera_id")
                url = data.get("url")
                
                if command == "start_camera":
                    pool.add_camera(cam_id, url)
                elif command == "stop_camera":
                    pool.remove_camera(cam_id)
                elif command == "sync_cameras":
                    pool.sync_cameras(data.get("cameras", []))
            except Exception as e:
                logger.error(f"Error processing command: {e}")

if __name__ == "__main__":
    main()
