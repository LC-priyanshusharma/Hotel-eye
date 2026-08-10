# LogicEye Current Architecture

## 1. Overview
The LogicEye system currently operates as a modular monolith running in Python via FastAPI. The system is designed to handle multiple concurrent RTSP/video streams, apply AI models (YOLO, InsightFace) dynamically via a plugin architecture, persist actionable events into PostgreSQL/TimescaleDB, and stream annotated MJPEG video to a React frontend.

## 2. Core Video Ingestion Path
The primary video ingestion is managed by `CameraManager` (`backend/core/camera_manager.py`).
1. **Source Connection**: When a camera is started, `CameraManager` instantiates a `StreamReader` thread.
2. **OpenCV Thread**: `StreamReader` uses `cv2.VideoCapture` to read frames in a blocking `while` loop. 
3. **Queueing**: Frames are placed into a bounded `queue.Queue` (size controlled by `config.FRAME_BUFFER_SIZE`). If the queue is full, the oldest frame is dropped to maintain low latency.
4. **Stale Frame Handling**: An "ECC Fast-Drop Algorithm" exists inside the `InferenceWorker`, which drains the queue of accumulated frames to prevent the AI thread from falling behind real-time.

## 3. Inference & Plugin Execution
1. **InferenceWorker Thread**: Each camera has a dedicated `InferenceWorker` thread that pulls the latest frame from the queue.
2. **Detection & Tracking**: The frame is passed to YOLO (via PyTorch) and tracked (DeepSORT/ByteTrack).
3. **Global FaceWorker**: A separate `FaceWorker` thread asynchronously processes faces to prevent heavy `InsightFace` execution from blocking the YOLO pipeline. It stores results in a shared `latest_results` dict.
4. **Plugins**: The `DetectionEngine` receives the frame, YOLO detections, tracking IDs, and face results, and executes enabled plugins (Visitor, ANPR, Fire, etc.) sequentially.
5. **Output**: The annotated frame and resulting events are pushed to an `output_queue`.

## 4. Event Generation & Database Persistence
1. **Event Bus**: The `output_queue` is consumed and events are published to Redis Streams (`logiceye:events`).
2. **Database Worker**: The `DatabaseWorker` thread (`backend/database/persistence.py`) listens to the Redis stream using a consumer group (`db_writers`).
3. **Filtering & Flushing**: It filters out non-actionable frames, accumulates actionable events in memory, and performs bulk inserts into PostgreSQL (with TimescaleDB for time-series) every second.

## 5. Streaming (MJPEG) Implementation
1. **State Management**: The main event loop stores the latest annotated frame in a global dictionary `LATEST_DATA[camera_id]`.
2. **Encoding (`streaming.py`)**: A `ThreadPoolExecutor` runs `cv2.imencode('.jpg')` to compress the raw frame to JPEG dynamically.
3. **Endpoints**: 
   - HTTP Polling/Streaming: `/video?camera_id=...` uses a FastApi generator.
   - WebSocket Broadcast: `video_broadcaster()` pushes JPEG bytes over WebSocket to active subscribers.
4. **Frontend (`VideoPlaceholder.tsx`)**: The React application renders the JPEG via standard `<img src="..."/>` tags (or WebSocket blob updates).

## 6. Discoveries & Bottlenecks
*   **MJPEG CPU Spikes**: Converting raw numpy arrays to JPEG dynamically in Python via OpenCV threads causes massive CPU loads when scaled beyond a few cameras.
*   **OpenCV Thread Blocking**: `cv2.VideoCapture.read()` can block indefinitely on unstable RTSP streams.
*   **Global Lock Contention**: `DATA_LOCK` wraps reads and writes to `LATEST_DATA`, which can cause micro-stutters when multiple threads (Inference, WebSockets, REST) contest it simultaneously.
*   **Lack of Hardware Decoding**: The current pipeline runs solely on CPU/Software decoding (OpenCV/FFmpeg) which restricts scalability.
*   **Coupled AI and Streaming**: The MJPEG stream inherently depends on the Python backend staying responsive. If Python threads lock or YOLO inference spikes, the video feed stalls.
