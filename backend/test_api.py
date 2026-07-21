from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)
response = client.post("/auth/login", json={"email":"admin@logiceye.ai", "password":"admin"})
print(response.status_code)
print(response.text)
