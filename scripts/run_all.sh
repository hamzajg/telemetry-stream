#!/usr/bin/env bash
set -euo pipefail

# Run the full local stack: start the API server, send sample events,
# then consume them into the lakehouse.
# Usage: ./scripts/run_all.sh [PORT] [EVENT_COUNT] [CONSUMER_ITERATIONS]
PORT="${1:-8001}"
EVENT_COUNT="${2:-5}"
CONSUMER_ITERATIONS="${3:-5}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Telemetry Stream Local Stack ==="
echo ""

cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}/src"

# Start server in background
echo "[1/3] Starting API server on port ${PORT}..."
python -m telemetry.serve server --host 127.0.0.1 --port "${PORT}" > "${REPO_DIR}/.run/backend.log" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "${REPO_DIR}/.run/backend.pid"

# Wait for server to be ready
for i in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:${PORT}/v1/devices" 2>/dev/null; then
    echo "  Server ready."
    break
  fi
  sleep 0.5
done

# Run producer
echo ""
echo "[2/3] Sending ${EVENT_COUNT} sample telemetry events..."
python -m telemetry.serve producer --count "${EVENT_COUNT}" --delay 0.5 --base-url "http://127.0.0.1:${PORT}"

# Run consumer
echo ""
echo "[3/3] Running consumer (${CONSUMER_ITERATIONS} iterations)..."
python -m telemetry.serve consumer --iterations "${CONSUMER_ITERATIONS}" --delay 0.5 --base-url "http://127.0.0.1:${PORT}"

# Stop server
echo ""
echo "Stopping API server..."
kill "${SERVER_PID}" 2>/dev/null || true
sleep 1
kill -9 "${SERVER_PID}" 2>/dev/null || true
rm -f "${REPO_DIR}/.run/backend.pid" "${REPO_DIR}/.run/backend.log"

echo ""
echo "=== Stack complete ==="
echo "Lakehouse data written to /tmp/telemetry-lakehouse"
