#!/bin/bash
# Arvis HQ — start server + open Cloudflare tunnel
# Usage: ./start.sh [--tunnel]

cd "$(dirname "$0")"

# Kill any existing server on port 8766
lsof -ti:8766 | xargs kill -9 2>/dev/null

# Start Flask server
python3 server.py &
SERVER_PID=$!
echo "Server started (pid $SERVER_PID) → http://localhost:8766"

# Optionally open Cloudflare tunnel for remote access
if [[ "$1" == "--tunnel" ]]; then
  echo "Starting Cloudflare tunnel..."
  cloudflared tunnel --url http://localhost:8766 2>&1 | grep -E "trycloudflare|https://" &
  echo "Tunnel URL will appear above — paste it into the dashboard on first remote visit."
fi

wait $SERVER_PID
