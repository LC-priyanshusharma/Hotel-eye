import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database.session import Base, get_async_db
from models.auth import User, Role, Permission
from app.auth.security import get_password_hash

# Use PostgreSQL test database
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://admin:admin@localhost:5432/cctv_test"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

async def override_get_async_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_async_db] = override_get_async_db

@pytest.fixture
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed DB with roles and superuser
    async with TestingSessionLocal() as db:
        admin_role = Role(name="admin")
        db.add(admin_role)
        await db.commit()
        
        perm = Permission(name="users:manage")
        db.add(perm)
        await db.commit()
        
        admin_role.permissions.append(perm)
        
        su = User(
            email="admin@logiceye.ai",
            hashed_password=get_password_hash("Admin@123!"),
            is_active=True,
            is_superuser=True
        )
        db.add(su)
        await db.commit()
        
        su.roles.append(admin_role)
        await db.commit()
        
    yield TestingSessionLocal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
