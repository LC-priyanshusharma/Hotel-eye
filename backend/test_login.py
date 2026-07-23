import asyncio
from database.session import async_engine, AsyncSessionLocal
from sqlalchemy.future import select
from models.auth import User
from app.auth.services import authenticate_user
from app.auth.schemas import LoginRequest

async def main():
    async with AsyncSessionLocal() as db:
        try:
            req = LoginRequest(email="admin@logiceye.ai", password="admin")
            await authenticate_user(db, req)
            print("SUCCESS")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
