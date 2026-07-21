from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.session import Base

class GarbageEvent(Base):
    __tablename__ = "garbage_events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    timestamp = Column(Float, index=True)
    category = Column(String, index=True)
    confidence = Column(Float)
    duration_seconds = Column(Float)
    zone_polygon = Column(JSON) # Store ROI or coordinates

    # Relationship to snapshot
    snapshot = relationship("GarbageSnapshot", back_populates="event", uselist=False)

class GarbageSnapshot(Base):
    __tablename__ = "garbage_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("garbage_events.id"))
    full_frame_path = Column(String)
    crop_path = Column(String)

    event = relationship("GarbageEvent", back_populates="snapshot")

class GarbageAnalytics(Base):
    __tablename__ = "garbage_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    date_bucket = Column(String, index=True) # e.g. "2026-07-18" or "2026-07-18T14:00"
    total_events = Column(Integer, default=0)
    category_breakdown = Column(JSON) # e.g. {"plastic bottle": 5, "cup": 2}
