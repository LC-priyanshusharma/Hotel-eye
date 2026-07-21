from sqlalchemy import Column, Integer, String, DateTime, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from database.session import Base
from datetime import datetime

class CameraEvent(Base):
    __tablename__ = "camera_events"
    
    # Note: In a production TimescaleDB setup, `timestamp` and `camera_id` 
    # would form a composite key or hypertable index, but we keep an ID for ORM simplicity initially.
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # JSONB allows us to save dynamic plugin outputs without schema migrations
    events = Column(JSONB, nullable=False)
    
    __table_args__ = (
        Index('idx_camera_timestamp', 'camera_id', 'timestamp'),
    )
