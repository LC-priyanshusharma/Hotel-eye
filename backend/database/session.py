from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from config.config import config

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

# SQLAlchemy Asynchronous Engine (For new Auth / Web endpoints)
# Convert sqlite:/// URL to sqlite+aiosqlite:///
async_db_url = config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
if "postgres" in async_db_url:
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    async_db_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine, 
    class_=AsyncSession
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
