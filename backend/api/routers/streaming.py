from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from fastapi.responses import StreamingResponse
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.state import LATEST_DATA, DATA_LOCK
from core.renderer import renderer

router = APIRouter(tags=["Streaming"])

# Shared thread pool for all MJPEG rendering streams to avoid blocking the main AsyncIO loop
mjpeg_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="MJPEG_Render")

def _verify_stream_token(token: str) -> bool:
    """Lightweight JWT verification for MJPEG streams.
    Only checks the signature — does NOT hit the database.
    This avoids the async DB session issue that causes 401 on <img> tags."""
    from app.auth.security import decode_access_token
    payload = decode_access_token(token)
    return payload is not None

def _render_and_encode(camera_id: str, packet: dict, quality: int = 70) -> bytes:
    """CPU-bound task for drawing overlays and JPEG compression."""
    import cv2
    import traceback
    try:
        annotated_frame = renderer.render_frame(camera_id, packet)
        # Compress JPEG dynamically based on requested quality
        ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ret:
            return buffer.tobytes()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").error(f"MJPEG RENDER ERROR: {traceback.format_exc()}")
    return b''

from pydantic import BaseModel

ACTIVE_STREAMS = {} # stream_id -> asyncio.Event

class KillStreamRequest(BaseModel):
    stream_id: str

@router.post("/kill-stream")
def kill_stream(req: KillStreamRequest):
    if req.stream_id in ACTIVE_STREAMS:
        ACTIVE_STREAMS[req.stream_id].set()
    return {"status": "killed"}

async def generate_mjpeg(request: Request, camera_id: str, quality: int = 70, stream_id: str = None):
    """Generator for MJPEG stream with AsyncIO offloading."""
    last_ts = 0
    loop = asyncio.get_running_loop()
    
    kill_event = None
    if stream_id:
        kill_event = asyncio.Event()
        ACTIVE_STREAMS[stream_id] = kill_event
    
    timeout_counter = 0
    try:
        while True:
            if await request.is_disconnected():
                break
                
            if kill_event and kill_event.is_set():
                break
                
            with DATA_LOCK:
                packet = LATEST_DATA.get(camera_id)
                
            if packet is None:
                # Camera is starting or broken. Give it up to 30 seconds (300 * 0.1s) to produce its first frame
                # Heavy YOLO models or concurrent starts can delay the first frame
                if timeout_counter > 300:
                    logger.warning(f"MJPEG Stream {stream_id} for {camera_id} timed out waiting for first frame.")
                    break
                timeout_counter += 1
                await asyncio.sleep(0.1)
                continue
        
            is_heartbeat = False
            if packet.get("timestamp", 0) == last_ts:
                # If no new frame, wait a bit
                await asyncio.sleep(0.05)
                # Send a heartbeat frame every 1 second (20 * 0.05s) to keep connection alive
                if timeout_counter > 20:
                    is_heartbeat = True
                    timeout_counter = 0
                else:
                    timeout_counter += 1
                    continue
            else:
                # New frame arrived, reset timeout counter
                timeout_counter = 0
                    
            if not is_heartbeat:
                last_ts = packet.get("timestamp", 0)
                
            # Offload CPU-bound rendering to the thread pool
            frame_bytes = await loop.run_in_executor(
                mjpeg_executor, 
                _render_and_encode, 
                camera_id, 
                packet,
                quality
            )
            
            if not frame_bytes:
                await asyncio.sleep(0.05)
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Yield to event loop, rate limited naturally by inference speed
            await asyncio.sleep(0.01)
    finally:
        if stream_id and stream_id in ACTIVE_STREAMS:
            del ACTIVE_STREAMS[stream_id]

@router.get("/video")
def video_feed(request: Request, camera_id: str, token: str = Query(None), quality: int = Query(70), stream_id: str = Query(None)):
    """
    MJPEG streaming endpoint.
    Uses lightweight JWT signature check (no DB lookup) to avoid async/sync issues.
    Usage: /video?camera_id=...&token=...&quality=70
    """
    if not token or not _verify_stream_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing stream token"
        )
    return StreamingResponse(generate_mjpeg(request, camera_id, quality, stream_id), media_type="multipart/x-mixed-replace; boundary=frame")

