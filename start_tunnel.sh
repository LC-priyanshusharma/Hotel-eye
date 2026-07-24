#!/bin/bash
cloudflared tunnel --url http://localhost:5173 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!

echo "Waiting for Cloudflare URL..."
URL=""
for i in {1..30}; do
    URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1)
    if [ -n "$URL" ]; then
        break
    fi
    sleep 1
done

if [ -n "$URL" ]; then
    echo "Found URL: $URL"
    # Overwrite the existing line in frontend/.env
    sed -i '' "s|VITE_PUBLIC_URL=.*|VITE_PUBLIC_URL=$URL|" frontend/.env
    echo "Updated frontend/.env"
else
    echo "Failed to get Cloudflare URL"
    cat /tmp/cloudflared.log
    kill $TUNNEL_PID
    exit 1
fi
