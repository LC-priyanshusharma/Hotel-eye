from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database.session import get_db

from app.plugins.anpr.repository import ANPRRepository
from app.plugins.anpr.schemas import (
    WatchlistCreate, WatchlistUpdate, WatchlistResponse,
    ANPREventResponse, PlateHistoryResponse, PlateStatisticsResponse
)
from app.plugins.anpr.models import ANPREvent, ANPRWatchlist, ANPRPlateHistory, ANPRStatistics

router = APIRouter(prefix="/anpr", tags=["ANPR"])

@router.get("/events", response_model=List[ANPREventResponse])
def get_recent_events(limit: int = 50, db: Session = Depends(get_db)):
    events = db.query(ANPREvent).order_by(ANPREvent.timestamp.desc()).limit(limit).all()
    return events

@router.get("/stats", response_model=PlateStatisticsResponse)
def get_anpr_stats(db: Session = Depends(get_db)):
    from datetime import datetime, time
    today = datetime.combine(datetime.now().date(), time.min)
    
    total_reads = db.query(ANPRPlateHistory).filter(ANPRPlateHistory.timestamp >= today.timestamp()).count()
    unique_plates = db.query(ANPRPlateHistory.plate_number).filter(ANPRPlateHistory.timestamp >= today.timestamp()).distinct().count()
    
    return PlateStatisticsResponse(
        total_reads_today=total_reads,
        unique_vehicles=unique_plates,
        watchlist_matches=0,
        average_accuracy=98.4
    )

@router.get("/search", response_model=List[PlateHistoryResponse])
def search_plate_history(
    plate: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(ANPRPlateHistory)
    if plate:
        query = query.filter(ANPRPlateHistory.plate_number.ilike(f"%{plate}%"))
    if camera_id:
        query = query.filter(ANPRPlateHistory.camera_id == camera_id)
        
    return query.order_by(ANPRPlateHistory.timestamp.desc()).limit(limit).all()

@router.get("/watchlists", response_model=List[WatchlistResponse])
def get_watchlists(db: Session = Depends(get_db)):
    return db.query(ANPRWatchlist).all()

@router.post("/watchlists", response_model=WatchlistResponse)
def create_watchlist(watchlist: WatchlistCreate, db: Session = Depends(get_db)):
    db_watchlist = ANPRWatchlist(**watchlist.model_dump())
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist

@router.patch("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(watchlist_id: str, watchlist: WatchlistUpdate, db: Session = Depends(get_db)):
    db_watchlist = db.query(ANPRWatchlist).filter(ANPRWatchlist.id == watchlist_id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
        
    for key, value in watchlist.model_dump(exclude_unset=True).items():
        setattr(db_watchlist, key, value)
        
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist

@router.delete("/watchlists/{watchlist_id}")
def delete_watchlist(watchlist_id: str, db: Session = Depends(get_db)):
    db_watchlist = db.query(ANPRWatchlist).filter(ANPRWatchlist.id == watchlist_id).first()
    if not db_watchlist:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
        
    db.delete(db_watchlist)
    db.commit()
    return {"status": "deleted"}
