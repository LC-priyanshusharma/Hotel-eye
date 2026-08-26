#!/bin/bash
# LogicEye Daemon Launcher
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Stopping existing services..."
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "deepstream_pyds/main.py" 2>/dev/null || true
pkill -9 -f "vite" 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
sleep 1

mkdir -p "$DIR/logs"

echo "Starting Backend API..."
cd "$DIR/backend"
source .venv/bin/activate
export DATABASE_URL="postgresql://admin:admin@localhost:5433/cctv"
export REDIS_URL="redis://localhost:6379/0"
export PYTHONPATH="$DIR/backend:$PYTHONPATH"
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "$DIR/logs/backend.log" 2>&1 &

echo "Waiting for RTSP publishers to initialize..."
sleep 3

echo "Starting DeepStream Pipeline..."
cd "$DIR/deepstream_pyds"
export PYTHONPATH="$DIR/backend:$DIR/deepstream_pyds:$PYTHONPATH"
nohup python3 main.py > "$DIR/logs/deepstream.log" 2>&1 &

echo "Starting Frontend..."
cd "$DIR/frontend"
nohup npm run dev -- --host 0.0.0.0 --port 3000 > "$DIR/logs/frontend.log" 2>&1 &

sleep 2
echo "All LogicEye services launched successfully in background."
