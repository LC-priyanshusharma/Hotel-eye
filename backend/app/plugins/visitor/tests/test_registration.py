import pytest
import base64
import numpy as np
import cv2
from fastapi.testclient import TestClient
from app.plugins.visitor.router import router
from fastapi import FastAPI
from database.session import get_db

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def create_dummy_base64_image():
    # Create a 100x100 black image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"

def test_registration_endpoint_format():
    # Test if the API validates the request correctly
    b64_img = create_dummy_base64_image()
    payload = {
        "name": "Test User",
        "email": "test@logiceye.ai",
        "photo_front": b64_img,
        "photo_left": b64_img,
        "photo_right": b64_img
    }
    
    # We expect a 500 or 400 because the dummy image doesn't actually contain a face,
    # but the routing and schema validation should pass (not 422).
    # Since we don't have a mocked DB in this simple test, we just check schema.
    response = client.post("/visitor/register", json=payload)
    assert response.status_code != 422
