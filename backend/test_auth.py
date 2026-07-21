import asyncio
from datetime import timedelta
from database.session import SessionLocal
from models.auth import User
from app.auth.security import create_access_token
import requests

db = SessionLocal()
admin = db.query(User).filter_by(email="admin@logiceye.ai").first()
token = create_access_token(subject=str(admin.id), scopes=["users:manage"], expires_delta=timedelta(minutes=30))

r = requests.get("http://localhost:8000/api/config", headers={"Authorization": f"Bearer {token}"})
print(r.text)
