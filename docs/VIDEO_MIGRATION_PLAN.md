# LogicEye Video Migration Plan

## 1. Objective
To introduce a production-grade, highly scalable video streaming and processing architecture utilizing MediaMTX for RTSP relay, WebRTC for low-latency dashboard streaming, and GStreamer for AI ingestion pipelines, completely decoupling streaming from the AI processing workload. The target is safe, robust 50-camera scalability with future NVIDIA hardware compatibility (DeepStream).

## 2. Proposed Architecture Separation

### Path A: Dashboard Streaming (MediaMTX + WebRTC)
- **Role**: Serve live video to users independently of AI.
- **Workflow**: 
  - RTSP Camera `->` MediaMTX (configured independently).
  - MediaMTX `->` WebRTC Client (React Frontend).
- **Benefits**: Near-zero latency, vastly reduced Python backend CPU usage (MJPEG encoding eliminated), zero AI-blocking issues.

### Path B: AI Processing Pipeline (GStreamer)
- **Role**: Extract frames for AI inference without affecting the live UI stream.
- **Workflow**:
  - MediaMTX (or RTSP Camera directly) `->` GStreamer Python Backend `->` `appsink` (RGB frames).
  - GStreamer Buffer `->` YOLO `->` Tracking `->` Plugins `->` Event Engine.
- **Benefits**: Fine-grained pipeline control, optimized memory management, and compatibility with future hardware acceleration (NVDEC/DeepStream).

## 3. Phased Implementation Plan

### Phase A: Architecture Audit (Complete)
- Evaluated existing OpenCV/MJPEG threads, camera lifecycle, and Redis/PostgreSQL workers.

### Phase B: Video Source Abstraction (Preparation)
- **Action**: Create a clean interface `VideoSource` inside `backend/camera/source.py`. 
- **Goal**: Allow swapping the `cv2.VideoCapture` backend for a `GStreamerBackend` cleanly without disrupting the existing `InferenceWorker`.
- **Target Files**: `backend/camera/stream_reader.py`, `backend/camera/source.py`.

### Phase C: Implement GStreamer Backend
- **Action**: Introduce `backend/video/gstreamer/pipeline.py`.
- **Goal**: Replace the blocking `cv2` loop with a robust GStreamer pipeline string (e.g., `rtspsrc ! rtph264depay ! h264parse ! decodebin ! videoconvert ! appsink drop=true max-buffers=1`).
- **Target Files**: `backend/camera/source.py`.

### Phase D: Optimize AI Pipeline & Backpressure
- **Action**: Ensure the transition from the GStreamer `appsink` to YOLO operates strictly on a "latest-frame-wins" paradigm. Check bounding queue limits.
- **Goal**: Prevent frame accumulation. Allow configuration of plugin-specific target FPS.

### Phase E: Introduce MediaMTX Server
- **Action**: Set up `mediamtx.yml` configuration and integrate it into the `docker-compose.yml` stack.
- **Goal**: Have all active cameras routed into MediaMTX for relay.

### Phase F: WebRTC Dashboard Integration
- **Action**: Replace the `img` src polling/websockets in the React frontend (`VideoPlaceholder.tsx` / `CameraCard.tsx`) with a native WebRTC player pointing to the MediaMTX WebRTC API endpoint.
- **Goal**: Unload the Python backend from serving video. 

### Phase G: Deprecate MJPEG
- **Action**: Remove `/video` endpoints and MJPEG encoder `ThreadPoolExecutor` from `streaming.py`.
- **Goal**: Eliminate legacy CPU-heavy video encoding tasks.

### Phase H: Stress Testing & Benchmarking
- **Action**: Create RTSP simulators and progressively load test 1, 5, 10, 25, and 50 cameras. 
- **Goal**: Validate memory stability, CPU bounds, thread limits, and database insertion robustness under maximal load.

## 4. Risks & Mitigations
- **Compatibility Risks**: Moving from MJPEG to WebRTC requires modern browser compatibility (supported in all standard environments). The frontend needs robust WebRTC reconnection logic.
- **GStreamer Installation**: GStreamer requires system-level dependencies. The `Dockerfile` and macOS setup instructions must be updated.
- **Memory Copies**: Care must be taken not to create unnecessary Python object copies when extracting frames from GStreamer `appsink` buffers into NumPy arrays. Use proper buffer mapping.
