from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.limiter import limiter

from app.plugins.parking.router import parking_router
from app.plugins.attendance.router import attendance_router
from app.plugins.fire.router import fire_router
from app.plugins.visitor.router import router as visitor_router
from app.plugins.anpr.router import router as anpr_router
from app.auth.routes import router as auth_router
from app.auth.admin_routes import admin_router
from app.config_routes import config_router
from voice.api.routes import voice_router

# Import our new focused routers
from api.routers.cameras import router as cameras_router
from api.routers.websockets import router as websockets_router
from api.routers.system import router as system_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    from loguru import logger
    from core.camera_manager import camera_manager
    from config.config import config
    from database.persistence import DatabaseWorker
    from main import event_loop
    
    logger.info("Starting up FastAPI application and Camera Manager...")
    
    # 1. Start Database Worker
    db_worker = DatabaseWorker()
    db_worker.start()
    
    # 2. Start global event loop thread
    import queue
    result_queue = queue.Queue(maxsize=100)
    loop_thread = threading.Thread(target=event_loop, args=(result_queue,), daemon=True, name="EventLoop")
    loop_thread.start()
    
    # 2.5 Start DeepStream Consumer thread
    from main import ds_consumer
    ds_thread = threading.Thread(target=ds_consumer, args=(result_queue,), daemon=True, name="DSConsumer")
    ds_thread.start()
    
    # 3. Start Global Workers (FaceWorker for Visitor/Employee Detection)
    camera_manager.start_global_workers()
    
    # 4. Load active cameras from Database
    from database.session import SessionLocal
    from database.repositories.camera_repository import CameraRepository
    db = SessionLocal()
    try:
        repo = CameraRepository(db)
        cameras = repo.get_active_cameras()
        logger.info(f"Found {len(cameras)} active cameras in database.")
        
        plugins_config = config.CAMERA_PLUGINS
        
        for cam in cameras:
            # We no longer auto-start cameras on boot.
            # The user requested to manually start each camera from the Web UI.
            logger.info(f"Camera loaded (Stopped): {cam.name}. Awaiting manual start.")
    except Exception as e:
        logger.error(f"Failed to load cameras on startup: {e}")
    finally:
        db.close()
        
    yield
    
    logger.info("Initiating graceful shutdown of all camera pipelines...")
    
    # Get all active camera IDs
    active_cameras = list(camera_manager.running_cameras.keys())
    for cam_id in active_cameras:
        logger.info(f"Stopping pipeline for {cam_id} during shutdown...")
        camera_manager.stop_camera_pipeline(cam_id)
        
    logger.info("All pipelines stopped. Releasing global resources...")
    camera_manager.stop_global_workers()
    logger.info("Shutdown complete.")

app = FastAPI(title="LogicEye Enterprise API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Core system routes
app.include_router(system_router)
app.include_router(cameras_router)
app.include_router(websockets_router)

# Auth and config routes
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(config_router)

# Plugin routes
app.include_router(parking_router)
app.include_router(attendance_router)
app.include_router(fire_router)
app.include_router(visitor_router, prefix="/api/plugins")
app.include_router(anpr_router, prefix="/api/plugins")
app.include_router(voice_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since we need wildcard for dev, allow_credentials must be False
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

os.makedirs("snapshots", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="snapshots"), name="snapshots")

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    print(f"Warning: Frontend dist directory not found at {frontend_dist}. UI will not be served natively.")
