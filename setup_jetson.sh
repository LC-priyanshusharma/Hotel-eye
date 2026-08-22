#!/bin/bash
set -e

echo "OrinNX@2026" | sudo -S apt update
echo "OrinNX@2026" | sudo -S apt install -y python3-venv python3-dev libpq-dev gcc g++ libgl1-mesa-glx nodejs npm

cd /home/user/LogicEye-main/backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations (will connect to local timescaledb)
export DATABASE_URL="postgresql://admin:admin@localhost:5432/cctv"
alembic upgrade head

echo "Backend setup complete."

cd /home/user/LogicEye-main/frontend
npm install
npm run build
echo "Frontend build complete."
