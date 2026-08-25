#!/bin/bash
set -e

echo "OrinNX@2026" | sudo -S apt update
echo "OrinNX@2026" | sudo -S apt install -y python3-venv python3-dev libpq-dev gcc g++ libgl1-mesa-glx curl

# Upgrade to Node.js 20 LTS (Required by Vite 6 / React 18 / TypeScript)
if ! command -v node &> /dev/null || [ "$(node -v | cut -d'.' -f1 | tr -d 'v')" -lt 20 ]; then
    echo "Upgrading Node.js to v20 LTS..."
    sudo apt-get remove -y libnode-dev libnode72 2>/dev/null || true
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
    sudo dpkg --force-overwrite -i /var/cache/apt/archives/nodejs*.deb 2>/dev/null || true
    sudo apt-get install -y --fix-broken nodejs
fi

cd /home/user/LogicEye-main/backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

# Ensure TimescaleDB and Redis containers are running for migrations
cd /home/user/LogicEye-main
docker compose up -d timescaledb redis mediamtx
echo "Waiting for database to be ready..."
sleep 4

cd /home/user/LogicEye-main/backend
export DATABASE_URL="postgresql://admin:admin@localhost:5433/cctv"
alembic upgrade head

echo "Backend and Database setup complete."

cd /home/user/LogicEye-main/frontend
npm install
npm run build
echo "Frontend build complete."
