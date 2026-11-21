#!/usr/bin/env bash
set -euo pipefail

# Start the telemetry-stream API server in the background.
# Usage: ./scripts/run_backend.sh [PORT]
PORT="${1:-8000}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting telemetry-stream API server on port ${PORT}..."
cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}/src"
python -m telemetry.serve server --host 127.0.0.1 --port "${PORT}" > "${REPO_DIR}/.run/backend.log" 2>&1 &
echo $! > "${REPO_DIR}/.run/backend.pid"

# Wait for the server to be ready
for i in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:${PORT}/v1/devices" 2>/dev/null; then
    echo "Server ready on http://127.0.0.1:${PORT}"
    exit 0
  fi
  sleep 0.5
done

echo "Server failed to start. Check ${REPO_DIR}/.run/backend.log"
exit 1
