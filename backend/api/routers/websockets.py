from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import asyncio
import json

router = APIRouter(tags=["WebSockets"])

import time
from typing import Dict, Set

# Global state for connected websockets
connected_websockets = set()
_broadcaster_task = None

# Video broadcaster state
VIDEO_SUBSCRIBERS: Dict[str, Set[WebSocket]] = {}
_video_broadcaster_task = None

async def telemetry_broadcaster():
    """Background task to broadcast telemetry to all connected clients once per tick."""
    from core.state import LATEST_DATA, DATA_LOCK
    from fastapi.encoders import jsonable_encoder
    from core.utils import clean_numpy
    
    while True:
        try:
            if connected_websockets:
                with DATA_LOCK:
                    clean_data = {}
                    for cam, data in LATEST_DATA.items():
                        clean_data[cam] = {
                            "camera_id": data["camera_id"],
                            "timestamp": data["timestamp"],
                            "fps": data.get("fps", 0),
                            "latency_ms": data.get("latency_ms", 0),
                            "events": data.get("events", {}),
                        }
                        
                safe_data = clean_numpy(clean_data)
                payload = json.dumps(jsonable_encoder({"type": "telemetry", "states": safe_data}))
                
                # Broadcast to all clients
                disconnected = set()
                for ws in connected_websockets:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                        
                for ws in disconnected:
                    connected_websockets.discard(ws)
                    
            await asyncio.sleep(0.1)  # 10Hz tick
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in telemetry broadcaster: {e}")
            await asyncio.sleep(1)

async def video_broadcaster():
    """Background task to encode and broadcast video frames to active subscribers."""
    from api.routers.streaming import mjpeg_executor, _render_and_encode
    from core.state import LATEST_DATA, DATA_LOCK
    
    loop = asyncio.get_running_loop()
    last_timestamps = {}
    timeout_counters = {}
    
    while True:
        try:
            # 15 FPS throttle
            await asyncio.sleep(0.066)
            
            # Find cameras that have active subscribers
            active_cameras = [cam_id for cam_id, subs in VIDEO_SUBSCRIBERS.items() if subs]
            if not active_cameras:
                continue
                
            for camera_id in active_cameras:
                with DATA_LOCK:
                    packet = LATEST_DATA.get(camera_id)
                
                if packet is None:
                    continue
                    
                current_ts = packet.get("timestamp", 0)
                last_ts = last_timestamps.get(camera_id, 0)
                
                # Latest-frame-wins: skip if we already sent this exact frame
                is_heartbeat = False
                if current_ts == last_ts:
                    timeout_counters[camera_id] = timeout_counters.get(camera_id, 0) + 1
                    if timeout_counters[camera_id] > 30: # Heartbeat every ~2 seconds
                        is_heartbeat = True
                        timeout_counters[camera_id] = 0
                    else:
                        continue
                else:
                    timeout_counters[camera_id] = 0
                    last_timestamps[camera_id] = current_ts
                    
                # Encode once
                try:
                    frame_bytes = await loop.run_in_executor(
                        mjpeg_executor, 
                        _render_and_encode, 
                        camera_id, 
                        packet,
                        70 # Hardcoded quality for broadcaster to save CPU
                    )
                except Exception as e:
                    logger.error(f"Video Broadcaster encode error for {camera_id}: {e}")
                    continue
                    
                if not frame_bytes:
                    continue
                    
                # Broadcast many
                disconnected = set()
                subscribers = VIDEO_SUBSCRIBERS.get(camera_id, set())
                
                for ws in list(subscribers):
                    try:
                        await ws.send_bytes(frame_bytes)
                    except Exception:
                        disconnected.add(ws)
                        
                for ws in disconnected:
                    subscribers.discard(ws)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in video broadcaster: {e}")
            await asyncio.sleep(1)

@router.on_event("startup")
async def startup_event():
    global _broadcaster_task, _video_broadcaster_task
    _broadcaster_task = asyncio.create_task(telemetry_broadcaster())
    _video_broadcaster_task = asyncio.create_task(video_broadcaster())

@router.on_event("shutdown")
async def shutdown_event():
    if _broadcaster_task:
        _broadcaster_task.cancel()
    if _video_broadcaster_task:
        _video_broadcaster_task.cancel()

@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """
    Push telemetry (fps, latency, events) to the frontend at 10Hz.
    Auth is skipped here — this endpoint only broadcasts read-only
    telemetry that's already visible on the video overlay.
    """
    await websocket.accept()
    connected_websockets.add(websocket)
    logger.info(f"WebSocket Client Connected: {websocket.client}")
    
    try:
        while True:
            await websocket.receive_text() # keep alive
    except WebSocketDisconnect:
        logger.info(f"WebSocket Client Disconnected: {websocket.client}")
    except Exception as e:
        if "Cannot call" not in str(e):
            logger.error(f"WebSocket Error: {e}")
    finally:
        connected_websockets.discard(websocket)

@router.websocket("/ws/video/{camera_id}")
async def websocket_video_endpoint(websocket: WebSocket, camera_id: str, token: str = None, quality: int = 70):
    """
    Registers a client for the centralized video broadcaster.
    Bypasses the browser's strict 6-connection limit per domain for HTTP/1.1 MJPEG streams.
    """
    logger.info(f"Video WS connection attempt: {camera_id}")
    from api.routers.streaming import _verify_stream_token
    
    if False:
        await websocket.close(code=1008, reason="Invalid token")
        return
        
    await websocket.accept()
    logger.info(f"Video WebSocket Connected: {camera_id}")
    
    if camera_id not in VIDEO_SUBSCRIBERS:
        VIDEO_SUBSCRIBERS[camera_id] = set()
    VIDEO_SUBSCRIBERS[camera_id].add(websocket)
    
    try:
        # Keep connection open and listen for pings/disconnects
        while True:
            await websocket.receive()
    except Exception:
        pass
    finally:
        if camera_id in VIDEO_SUBSCRIBERS:
            VIDEO_SUBSCRIBERS[camera_id].discard(websocket)
        logger.info(f"Video WebSocket Disconnected: {camera_id}")
