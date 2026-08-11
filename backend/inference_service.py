import torch
import numpy as np
import io
import json
import redis
import time
import os
import base64
from PIL import Image

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "detection/yolo11n.torchscript")

class YOLOInfer:
    def __init__(self):
        print(f"Loading TorchScript model from {MODEL_PATH}...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = torch.jit.load(MODEL_PATH, map_location=self.device)
        self.model.eval()
        print(f"Model loaded successfully on {self.device}.")

    def preprocess(self, img_bytes):
        # Resize to 640x640, RGB
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_w, orig_h = img.size
        resized = img.resize((640, 640), Image.BILINEAR)
        rgb = np.array(resized)
        # HWC to CHW, /255.0
        chw = rgb.transpose((2, 0, 1)).astype(np.float32)
        chw /= 255.0
        tensor = torch.from_numpy(chw).unsqueeze(0).to(self.device)
        return tensor, orig_w, orig_h

    def infer(self, img_bytes, conf_thresh=0.25, iou_thresh=0.45):
        tensor, orig_w, orig_h = self.preprocess(img_bytes)
        
        with torch.no_grad():
            output = self.model(tensor)
        
        # output is a tuple if it's YOLO11, or a single tensor.
        # usually shape is (1, 84, 8400)
        if isinstance(output, tuple):
            output = output[0]
            
        output = output.cpu().numpy()[0] # (84, 8400)
        
        return self.postprocess(output, orig_w, orig_h, conf_thresh, iou_thresh)

    def postprocess(self, output, orig_w, orig_h, conf_thresh, iou_thresh):
        output = output.T # (8400, 84)
        boxes = []
        scores = []
        class_ids = []
        
        x_factor = orig_w / 640.0
        y_factor = orig_h / 640.0
        
        for row in output:
            classes_scores = row[4:]
            max_score = np.max(classes_scores)
            
            if max_score >= conf_thresh:
                class_id = np.argmax(classes_scores)
                x, y, w, h = row[0], row[1], row[2], row[3]
                
                left = int((x - w / 2) * x_factor)
                top = int((y - h / 2) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)
                
                boxes.append([left, top, width, height])
                scores.append(float(max_score))
                class_ids.append(int(class_id))
                
        def nms(boxes, scores, iou_thresh):
            if len(boxes) == 0: return []
            b = np.array(boxes)
            x1, y1 = b[:, 0], b[:, 1]
            x2, y2 = b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
            areas = (x2 - x1 + 1) * (y2 - y1 + 1)
            order = np.array(scores).argsort()[::-1]
            keep = []
            while order.size > 0:
                i = order[0]
                keep.append(i)
                xx1 = np.maximum(x1[i], x1[order[1:]])
                yy1 = np.maximum(y1[i], y1[order[1:]])
                xx2 = np.minimum(x2[i], x2[order[1:]])
                yy2 = np.minimum(y2[i], y2[order[1:]])
                w = np.maximum(0.0, xx2 - xx1 + 1)
                h = np.maximum(0.0, yy2 - yy1 + 1)
                inter = w * h
                iou = inter / (areas[i] + areas[order[1:]] - inter)
                inds = np.where(iou <= iou_thresh)[0]
                order = order[inds + 1]
            return keep

        indices = nms(boxes, scores, iou_thresh)
        results = []
        for i in indices:
            results.append({
                "box": boxes[i],
                "score": scores[i],
                "class_id": class_ids[i]
            })
        return results

def process_stream():
    inferer = YOLOInfer()
    print("Inference service started. Listening on Redis 'inference_queue'...")
    while True:
        try:
            response = redis_client.blpop(["inference_queue"], timeout=0)
            if not response: continue
            _, data = response
            payload = json.loads(data)
            
            frame_id = payload.get("frame_id")
            conf_thresh = payload.get("conf_thresh", 0.25)
            img_b64 = payload.get("image_b64")
            
            if not frame_id or not img_b64: continue
            img_bytes = base64.b64decode(img_b64)
            
            results = inferer.infer(img_bytes, conf_thresh=conf_thresh)
            result_payload = {"frame_id": frame_id, "results": results}
            result_key = f"inference_result_{frame_id}"
            redis_client.rpush(result_key, json.dumps(result_payload))
            redis_client.expire(result_key, 10)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.1)

if __name__ == "__main__":
    process_stream()
