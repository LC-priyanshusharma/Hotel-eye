import cv2
import json
import base64
import uuid
from loguru import logger
from detection.interfaces.inference import IInferenceEngine
from config.config import redis_client

class RedisInferenceStrategy(IInferenceEngine):
    """
    Acts as an RPC client for the Inference microservice over Redis.
    Encodes the numpy frame to JPEG to minimize bandwidth, pushes to the queue,
    and synchronously waits for the result via BLPOP.
    """
    def __init__(self, model_path: str, conf: float, classes: list):
        self.model_path = model_path
        self.conf = conf
        self.classes = classes
        logger.info("Initialized RedisInferenceStrategy RPC client.")

    def detect(self, img, conf=0.25, classes=None):
        if classes is None:
            classes = self.classes
            
        try:
            # 1. Encode frame to JPEG
            # We resize first if it's huge, but inference service also resizes.
            # Just encode the raw numpy array (OpenCV BGR format)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            success, encoded_img = cv2.imencode('.jpg', img, encode_param)
            
            if not success:
                logger.error("Failed to encode frame for Redis inference.")
                return []
                
            img_b64 = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
            frame_id = str(uuid.uuid4())
            
            # 2. Prepare payload
            payload = {
                "frame_id": frame_id,
                "conf_thresh": conf,
                "image_b64": img_b64
            }
            
            # 3. Publish to queue
            queue_name = "inference_queue"
            result_key = f"inference_result_{frame_id}"
            
            redis_client.rpush(queue_name, json.dumps(payload))
            
            # 4. Wait for result (BLPOP blocks until item is available or timeout)
            # Timeout is 2 seconds (if inference container is down or overloaded)
            response = redis_client.blpop([result_key], timeout=2)
            
            if response is None:
                logger.warning(f"Inference timeout for frame {frame_id}")
                return []
                
            # BLPOP returns a tuple (queue_name, data)
            _, data_bytes = response
            data_str = data_bytes
            
            result_payload = json.loads(data_str)
            
            if "error" in result_payload:
                logger.error(f"Inference container error: {result_payload['error']}")
                return []
                
            # Parse bounding boxes
            detections = []
            for item in result_payload.get("results", []):
                # Only include classes we care about
                if classes and item["class_id"] not in classes:
                    continue
                    
                detections.append([
                    item["box"],      # [x, y, w, h]
                    item["score"],    # confidence
                    item["class_id"]  # class_id
                ])
                
            return detections
            
        except Exception as e:
            logger.error(f"Redis inference failed: {e}")
            return []
