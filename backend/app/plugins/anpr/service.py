import asyncio
from typing import Dict, Any
from loguru import logger
from database.session import SessionLocal
from app.plugins.anpr.repository import ANPRRepository

class ANPRService:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1000)
        self.worker_task = None
        
    async def start(self):
        if not self.worker_task:
            self.worker_task = asyncio.create_task(self._process_queue())
            logger.info("ANPR Service worker started.")

    async def stop(self):
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("ANPR Service worker stopped.")

    async def enqueue_finalized_track(self, track_data: Dict[str, Any]):
        try:
            await self.queue.put(track_data)
        except asyncio.QueueFull:
            logger.error("ANPR Service queue is full. Dropping track data.")

    async def _process_queue(self):
        while True:
            try:
                track_data = await self.queue.get()
                self._handle_track(track_data)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing ANPR track data: {e}")

    def _handle_track(self, track_data: Dict[str, Any]):
        db = SessionLocal()
        try:
            repo = ANPRRepository(db)
            
            # Log the track
            repo.create_vehicle_track(track_data["track_info"])
            
            best_plate = track_data["track_info"].get("best_plate")
            if best_plate:
                # Log to plate history
                history_data = {
                    "plate_number": best_plate,
                    "confidence": track_data["track_info"].get("plate_confidence", 0.0),
                    "timestamp": track_data["track_info"]["start_time"],
                    "camera_id": track_data["track_info"]["camera_id"],
                    "track_id": track_data["track_info"]["track_id"],
                    "vehicle_snapshot": track_data["track_info"].get("vehicle_snapshot"),
                    "plate_snapshot": track_data["track_info"].get("plate_snapshot"),
                }
                repo.log_plate_history(history_data)
                
                # Check watchlist
                match = repo.get_watchlist_match(best_plate)
                if match:
                    # In a real system, emit WS event specifically for this match
                    logger.warning(f"WATCHLIST MATCH: {best_plate} (Type: {match.list_type})")
                    repo.create_event({
                        "event_type": f"{match.list_type.upper()}_MATCH",
                        "plate_number": best_plate,
                        "confidence": track_data["track_info"].get("plate_confidence", 0.0),
                        "timestamp": track_data["track_info"]["start_time"],
                        "camera_id": track_data["track_info"]["camera_id"],
                        "track_id": track_data["track_info"]["track_id"]
                    })
        except Exception as e:
            logger.error(f"DB Error handling ANPR track: {e}")
        finally:
            db.close()

anpr_service = ANPRService()
