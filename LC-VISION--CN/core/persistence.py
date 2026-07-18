import threading
import queue
import time
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from db.session import SessionLocal, engine, Base
from db.models import CameraEvent

class DatabaseWorker:
    """
    Background worker thread dedicated to writing events to PostgreSQL/TimescaleDB.
    
    It reads from the global result queue, drops the heavy video frame, 
    and performs bulk inserts to maximize throughput without blocking AI.
    """
    def __init__(self, result_queue: queue.Queue):
        self.result_queue = result_queue
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.batch_size = 50
        self.flush_interval = 2.0  # Force a DB write every 2 seconds minimum

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        
        # Ensure tables exist (we will rely on Alembic for prod, but this is a failsafe)
        Base.metadata.create_all(bind=engine)
        
        self._thread = threading.Thread(target=self._run, daemon=True, name="DatabaseWorker")
        self._thread.start()
        logger.info("Started Database Worker thread.")

    def stop(self):
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("Stopped Database Worker thread.")

    def _run(self):
        logger.info("Database Worker active and listening for events...")
        
        batch = []
        last_flush = time.time()
        
        while self.is_running:
            try:
                # We peek/read from the queue. Wait, if we 'get', we consume it.
                # In main.py, event_loop gets from result_queue to feed the API.
                # We need a separate queue for DB, OR main.py pushes to both, OR we broadcast.
                # Let's adjust this: main.py will push to db_queue.
                packet = self.result_queue.get(timeout=0.1)
                
                db_event = CameraEvent(
                    camera_id=packet["camera_id"],
                    timestamp=datetime.fromtimestamp(packet["timestamp"], timezone.utc),
                    events=packet["events"]
                )
                batch.append(db_event)
                
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Error processing event for DB: {e}")
                
            # Flush conditions
            if len(batch) >= self.batch_size or (time.time() - last_flush) > self.flush_interval:
                if batch:
                    self._flush(batch)
                    batch = []
                last_flush = time.time()
                
        # Final flush on graceful shutdown
        if batch:
            self._flush(batch)

    def _flush(self, batch):
        db: Session = SessionLocal()
        try:
            db.add_all(batch)
            db.commit()
            logger.debug(f"Flushed {len(batch)} events to PostgreSQL.")
        except Exception as e:
            logger.error(f"Failed to bulk insert to database: {e}")
            db.rollback()
        finally:
            db.close()
