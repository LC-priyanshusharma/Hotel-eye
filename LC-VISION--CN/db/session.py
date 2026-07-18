from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import config

# SQLAlchemy Synchronous Engine
# We use standard pooling since our background worker handles the DB writes.
engine = create_engine(
    config.DATABASE_URL, 
    pool_size=5, 
    max_overflow=10,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
