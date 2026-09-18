#!/bin/bash

# Kill any existing process on port 8000 before starting
if command -v lsof &>/dev/null; then
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
else
  # Windows fallback via netstat + taskkill
  for pid in $(netstat -ano 2>/dev/null | grep ":8000 " | grep "LISTENING" | awk '{print $5}' | sort -u); do
    taskkill //PID "$pid" //F 2>/dev/null || true
  done
fi

# This WiFi has client/AP isolation, so a phone on the same network still can't reach this
# computer by LAN IP - Expo Go's fetch() calls to the backend need a public URL instead (Expo's
# own --tunnel flag only tunnels the Metro/JS bundler connection, not the app's own fetch()
# calls). Start a Cloudflare quick tunnel in the background and write the generated URL into
# frontend/services/api.js automatically, before the server itself takes over this terminal.
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
CLOUDFLARED_BIN="/c/tools/cloudflared/cloudflared.exe"
DEV_LOG_DIR="$REPO_ROOT/.dev"
TUNNEL_LOG="$DEV_LOG_DIR/cloudflared.log"
API_JS="$REPO_ROOT/frontend/services/api.js"

mkdir -p "$DEV_LOG_DIR"

if [ ! -f "$CLOUDFLARED_BIN" ]; then
  echo "Downloading cloudflared..."
  mkdir -p "$(dirname "$CLOUDFLARED_BIN")"
  curl -sL -o "$CLOUDFLARED_BIN" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
fi

echo "Starting Cloudflare tunnel..."
"$CLOUDFLARED_BIN" tunnel --url http://localhost:8000 > "$TUNNEL_LOG" 2>&1 &

TUNNEL_URL=""
for i in $(seq 1 30); do
  TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
  sleep 1
done

if [ -n "$TUNNEL_URL" ]; then
  sed -i "s#const TUNNEL_URL = '.*';#const TUNNEL_URL = '$TUNNEL_URL';#" "$API_JS"
  echo "Tunnel URL: $TUNNEL_URL (written to frontend/services/api.js)"
else
  echo "Warning: could not find a tunnel URL after 30s - check $TUNNEL_LOG"
fi

cd backend
~/.pyenv/pyenv-win/versions/3.11.9/python.exe -m venv venv
source venv/Scripts/activate
./run_api.sh