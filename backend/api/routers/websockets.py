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
                            "camera_id": data.get("camera_id", cam),
                            "timestamp": data.get("timestamp", 0),
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

# Removed video_broadcaster (deprecated in favor of WebRTC via MediaMTX)

@router.on_event("startup")
async def startup_event():
    global _broadcaster_task
    _broadcaster_task = asyncio.create_task(telemetry_broadcaster())

@router.on_event("shutdown")
async def shutdown_event():
    if _broadcaster_task:
        _broadcaster_task.cancel()

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

# Removed /ws/video/{camera_id} endpoint (deprecated in favor of WebRTC via MediaMTX)
