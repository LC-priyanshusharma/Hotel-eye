from database.session import SessionLocal
from models.auth import User
from app.auth.security import get_password_hash

db = SessionLocal()
existing = db.query(User).filter_by(email="admin@logiceye.ai").first()
if not existing:
    admin = User(
        email="admin@logiceye.ai",
        hashed_password=get_password_hash("admin"),
        is_superuser=True,
        is_active=True
    )
    db.add(admin)
    db.commit()
    print("Admin user created successfully!")
else:
    print("Admin user already exists!")
