#!/bin/bash
# run_local.sh
# Script to run LogicEye backend and frontend locally outside of Docker

echo "==============================================="
echo " Starting LogicEye Platform Locally"
echo "==============================================="

# Setup Cleanup trap early
# Fix: Wait for BACKEND_PID to exit gracefully so OpenCV doesn't segfault and Redis/Postgres aren't killed early
trap "echo 'Shutting down...'; [ -n \"\$TUNNEL_PID\" ] && kill -9 \$TUNNEL_PID 2>/dev/null; [ -n \"\$FFMPEG_PIDS\" ] && kill -9 \$FFMPEG_PIDS 2>/dev/null; if kill -0 \$BACKEND_PID 2>/dev/null; then kill \$BACKEND_PID 2>/dev/null; wait \$BACKEND_PID 2>/dev/null; fi; docker-compose stop timescaledb redis mediamtx" EXIT

# 1. Start Postgres & Redis (We still use docker for databases to avoid polluting host system)
echo "Ensuring Databases are running via Docker..."
docker-compose up -d timescaledb redis mediamtx

echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T timescaledb pg_isready -U admin -d cctv; do
  sleep 1
done
echo "PostgreSQL is ready!"

# 2. Cleanup orphaned processes
echo "Cleaning up any orphaned backend/frontend processes..."
lsof -ti :8000,5173 | xargs kill -9 2>/dev/null || true

# 3. Start Backend in background
echo "Starting FastAPI Backend..."
cd backend
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "Installing/Updating requirements using uv (blazing fast resolver)..."
pip install uv
uv pip install -r requirements.txt
export DATABASE_URL="postgresql://admin:admin@localhost:5433/cctv"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="super-secret-key-1234-must-be-at-least-32-bytes"

# Clear temporary ffmpeg config if it exists
rm -f ffmpeg_cams.txt

# Ensure test cameras are in the DB
python3 -c "
import sys, os, uuid
sys.path.append(os.getcwd())
from database.session import SessionLocal
from database.models.models import Camera
db = SessionLocal()
try:
    videos = [
        ('CHECK IN.mp4', 'Check In Camera'),
        ('CHECK OUT.mp4', 'Check Out Camera'),
        ('hlo.mp4', 'ANPR Camera'),
        ('IMG_1441.MOV', 'ANPR Camera 2'),
        ('332263_medium.mp4', 'Carton Counting'),
        ('PARKING.mp4', 'Parking Camera'),
        ('WhatsApp Video 2026-07-27 at 14.55.41.mp4', 'Restriction Zone Camera'),
        ('people_counting.MOV', 'People Counting'),
        ('ppe and people_count.mp4', 'PPE Camera'),
        ('WhatsApp Video 2026-07-31 at 16.36.46.mp4', 'WhatsApp Camera')
    ]
    
    video_paths = []
    for filename, name in videos:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), filename))
        video_paths.append(abs_path)
        
    # Clean up old stale test cameras that are no longer in the list
    stale_cams = db.query(Camera).filter(Camera.source_type == 'file').all()
    for c in stale_cams:
        if c.rtsp_url not in video_paths:
            db.delete(c)
    db.commit()
    
    import json
    state_file = 'camera_plugins_state.json'
    state = {}
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
            
    for filename, name in videos:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), filename))
        if not os.path.exists(abs_path):
            continue
            
        existing = db.query(Camera).filter(Camera.rtsp_url == abs_path).first()
        if not existing:
            cam_id = str(uuid.uuid4())
            new_cam = Camera(id=cam_id, name=name, rtsp_url=abs_path, source_type='file', source=abs_path, active=True)
            db.add(new_cam)
            print(f'Added {filename} to DB as {name}')
        else:
            cam_id = existing.id
            
        if cam_id not in state:
            state[cam_id] = []
            
        with open('ffmpeg_cams.txt', 'a') as f:
            f.write(f'{cam_id}|{abs_path}\n')
            
    db.commit()
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
        
except Exception as e:
    print(f'Error adding test cams: {e}')
finally:
    db.close()
"

if [ -f "ffmpeg_cams.txt" ]; then
    echo "Waiting for MediaMTX to initialize port 8554..."
    sleep 3
    echo "Starting FFmpeg background streams to push local files to MediaMTX for WebRTC..."
    FFMPEG_PIDS=""
    while IFS="|" read -r cam_id abs_path; do
        ffmpeg -v error -re -stream_loop -1 -i "$abs_path" -c:v h264_videotoolbox -profile:v baseline -realtime true -b:v 2M -an -f rtsp -rtsp_transport tcp "rtsp://localhost:8554/$cam_id" > /dev/null 2>&1 &
        FFMPEG_PIDS="$FFMPEG_PIDS $!"
    done < ffmpeg_cams.txt
    rm -f ffmpeg_cams.txt
fi

# Fix macOS SIP stripping dynamic library paths for Homebrew installed PyGObject/GStreamer
export DYLD_FALLBACK_LIBRARY_PATH=/usr/local/lib:/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
python3 main.py &
BACKEND_PID=$!
cd ..

# 3. Start Frontend and Public QR Tunnel
echo "Starting Vite Frontend and QR Tunnel..."
cd frontend
npm install

# Start QR Tunnel using Cloudflare Tunnel (Avoids localtunnel phishing intercept page)
echo "Establishing secure public tunnel for QR access..."
npx -y cloudflared tunnel --url http://localhost:5173 > tunnel.log 2>&1 &
TUNNEL_PID=$!

# Poll for the URL up to 15 seconds (Cloudflare takes slightly longer to provision)
ATTEMPTS=0
PUBLIC_URL=""
while [ $ATTEMPTS -lt 15 ]; do
    PUBLIC_URL=$(grep -a -o 'https://.*\.trycloudflare\.com' tunnel.log | head -n 1)
    if [ -n "$PUBLIC_URL" ]; then
        break
    fi
    sleep 1
    ATTEMPTS=$((ATTEMPTS+1))
done

if [ -n "$PUBLIC_URL" ]; then
    echo "==============================================="
    echo " 🌐 QR Tunnel Active! Public URL: $PUBLIC_URL"
    echo " 📱 Scanning QR codes will now work globally from any network!"
    echo "==============================================="
    export VITE_PUBLIC_URL="$PUBLIC_URL"
else
    echo "⚠️ Failed to start tunnel within 10 seconds. Using local network IP for QR codes."
fi

echo "==============================================="
echo " ✅ SYSTEM IS FULLY RUNNING! "
echo " 🌐 Open your browser to the Local or Network URL below."
echo " 🛑 Press Ctrl+C at any time to gracefully shut down the platform."
echo "==============================================="
npm run dev
