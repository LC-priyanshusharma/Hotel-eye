from sqlalchemy.orm import Session
from app.plugins.anpr.models import ANPREvent, ANPRVehicleTrack, ANPRPlateHistory, ANPRWatchlist
from typing import List, Optional

class ANPRRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_event(self, event_data: dict) -> ANPREvent:
        db_event = ANPREvent(**event_data)
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event

    def create_vehicle_track(self, track_data: dict) -> ANPRVehicleTrack:
        db_track = ANPRVehicleTrack(**track_data)
        self.db.add(db_track)
        self.db.commit()
        self.db.refresh(db_track)
        return db_track

    def get_watchlist_match(self, plate_number: str) -> Optional[ANPRWatchlist]:
        return self.db.query(ANPRWatchlist).filter(ANPRWatchlist.plate_number == plate_number).first()
    
    def log_plate_history(self, history_data: dict) -> ANPRPlateHistory:
        db_history = ANPRPlateHistory(**history_data)
        self.db.add(db_history)
        self.db.commit()
        self.db.refresh(db_history)
        return db_history
