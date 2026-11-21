#!/usr/bin/env bash
set -euo pipefail

# Run the complete local stack: backend API server + frontend dev server.
# Usage: ./scripts/run_stack.sh [PORT]
PORT="${1:-8001}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="${REPO_DIR}/web"

echo "=== Telemetry Stream Full Stack ==="
echo ""

cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}/src"

# 1. Start the backend API server in the background
echo "[1/2] Starting backend API server on port ${PORT}..."
./scripts/run_backend.sh "${PORT}" > /dev/null

# Wait for backend readiness
for i in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:${PORT}/v1/devices" 2>/dev/null; then
    echo "  Backend ready."
    break
  fi
  sleep 0.5
done

# 2. Start the frontend dev server in the background
echo "[2/2] Starting frontend dev server..."
cd "${WEB_DIR}"
export VITE_API_BASE="http://127.0.0.1:${PORT}"
nohup npm run dev > "${REPO_DIR}/.run/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "${REPO_DIR}/.run/frontend.pid"

# Wait for frontend readiness
for i in $(seq 1 30); do
  if curl -s -o /dev/null "http://localhost:5173" 2>/dev/null; then
    echo "  Frontend ready."
    break
  fi
  sleep 0.5
done

echo ""
echo "=== Full stack running ==="
echo "Backend API:    http://127.0.0.1:${PORT}"
echo "Frontend UI:    http://localhost:5173"
echo ""
echo "API endpoints:"
echo "  POST   /v1/telemetry        - ingest an event"
echo "  GET    /v1/telemetry        - list telemetry events"
echo "  GET    /v1/devices          - device registry"
echo "  POST   /v1/devices/register - register a device"
echo "  GET    /v1/metrics          - observability counters + lag"
echo ""
echo "To send sample events: ./scripts/run_producer.sh 5 0.5 http://127.0.0.1:${PORT}"
echo "To stop everything:    ./scripts/stop_all.sh"
echo ""

# Keep the script alive so background processes stay attached to this session
echo "Press Ctrl+C to stop all services..."
wait "$FRONTEND_PID"
