from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database.persistence import Base

class Visitor(Base):
    __tablename__ = "visitors"

    visitor_id = Column(String, primary_key=True, index=True)
    google_form_submission_id = Column(String, index=True, nullable=True)
    name = Column(String, index=True)
    role = Column(String, default="VISITOR", index=True) # VISITOR or EMPLOYEE
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    face_embedding = Column(Vector(512), nullable=True) # 512-dimensional pgvector array
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    total_visits = Column(Integer, default=0)
    status = Column(String, default="REGISTERED") # REGISTERED, UNKNOWN
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    visits = relationship("Visit", back_populates="visitor")
    events = relationship("VisitorEvent", back_populates="visitor")


class Visit(Base):
    __tablename__ = "visits"

    visit_id = Column(String, primary_key=True, index=True)
    visitor_id = Column(String, ForeignKey("visitors.visitor_id"), index=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    camera_id = Column(String, nullable=False)
    track_id = Column(String, nullable=False)
    snapshot_path = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    visitor = relationship("Visitor", back_populates="visits")
    events = relationship("VisitorEvent", back_populates="visit")


class VisitorEvent(Base):
    __tablename__ = "visitor_events"

    event_id = Column(String, primary_key=True, index=True)
    visitor_id = Column(String, ForeignKey("visitors.visitor_id"), index=True)
    visit_id = Column(String, ForeignKey("visits.visit_id"), nullable=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now())
    camera = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    visitor = relationship("Visitor", back_populates="events")
    visit = relationship("Visit", back_populates="events")
