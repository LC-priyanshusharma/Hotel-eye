from app.auth.security import create_access_token
import requests

token = create_access_token({"sub": "admin@logiceye.ai"}, scopes=["users:manage"])
res = requests.post("http://localhost:8000/api/cameras/stop", json={"camera_id": "test-cam-0001"}, headers={"Authorization": f"Bearer {token}"})
print(res.json())

res2 = requests.get("http://localhost:8000/cameras/status", headers={"Authorization": f"Bearer {token}"})
print(res2.json())
