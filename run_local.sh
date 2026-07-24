#!/bin/bash
# run_local.sh
# Script to run LogicEye backend and frontend locally outside of Docker

echo "==============================================="
echo " Starting LogicEye Platform Locally"
echo "==============================================="

# 1. Start Postgres & Redis (We still use docker for databases to avoid polluting host system)
echo "Ensuring Databases are running via Docker..."
docker-compose up -d timescaledb redis
sleep 3

# 2. Start Backend in background
echo "Starting FastAPI Backend..."
cd backend
source .venv/bin/activate || echo "No .venv found, using system python"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# 3. Start Frontend in foreground
echo "Starting Vite Frontend..."
cd frontend
npm run dev

# Cleanup when script is killed (Ctrl+C)
trap "echo 'Shutting down...'; kill $BACKEND_PID" EXIT
