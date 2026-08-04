import sys, os
sys.path.append(os.getcwd())
from database.session import SessionLocal
from database.models.models import Camera
import json

db = SessionLocal()
try:
    filename = 'WhatsApp Video 2026-07-31 at 16.36.46.mp4'
    name = 'WhatsApp Camera'
    default_id = 'test-cam-whatsapp'
    # The file is in the root dir, so it's one level up from backend
    abs_path = os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), filename))
    
    if not os.path.exists(abs_path):
        print(f"File not found: {abs_path}")
        sys.exit(1)

    existing = db.query(Camera).filter(Camera.rtsp_url == abs_path).first()
    cam_id = default_id
    if not existing:
        new_cam = Camera(id=cam_id, name=name, rtsp_url=abs_path, source_type='file', source=abs_path, active=True)
        db.add(new_cam)
        print(f'Added {filename} to DB as {name}')
    else:
        cam_id = existing.id
        print(f'Camera {name} already exists in DB.')
        
    state_file = 'camera_plugins_state.json'
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
            
    if cam_id not in state:
        state[cam_id] = []
        
    db.commit()
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)

except Exception as e:
    print(f'Error adding camera: {e}')
finally:
    db.close()
