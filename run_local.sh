#!/bin/bash
# run_local.sh
# Master startup script for LogicEye on Jetson Nano

echo "==============================================="
echo " Starting LogicEye AI Platform on Jetson Nano"
echo "==============================================="

# 1. Enable X11 forwarding for DeepStream (required for local UI debugging)
if command -v xhost &> /dev/null; then
    xhost + > /dev/null 2>&1
    echo "Granted X11 access for DeepStream visualization."
fi

# 2. Cleanup old instances
echo "Stopping any existing containers..."
docker-compose down
[ -f .tunnel.pid ] && kill -9 $(cat .tunnel.pid) 2>/dev/null
rm -f .tunnel.pid tunnel.log

# 3. Start the fully Dockerized Jetson Stack
echo "Building and starting all containers (DeepStream, Backend, Frontend, DBs)..."
docker-compose up -d --build

# 4. Wait for Frontend Nginx to be ready
echo "Waiting for Frontend to come online..."
sleep 5

# 5. Start Secure Public Tunnel
echo "==============================================="
echo " 🌐 Starting Cloudflare Tunnel for Public Access..."
echo "==============================================="
# Forward traffic to the new Docker Nginx frontend on port 80
npx -y cloudflared tunnel --url http://localhost:80 > tunnel.log 2>&1 &
TUNNEL_PID=$!
echo $TUNNEL_PID > .tunnel.pid

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
else
    echo "⚠️ Failed to start tunnel within 15 seconds. Check tunnel.log."
fi

echo "==============================================="
echo " ✅ SYSTEM IS FULLY RUNNING! "
echo " 🌐 Access locally at: http://localhost"
echo " 🔍 To view logs: docker-compose logs -f"
echo " 🛑 To gracefully shut down, run: docker-compose down && kill -9 \$(cat .tunnel.pid)"
echo "==============================================="
