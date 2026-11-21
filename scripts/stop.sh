#!/usr/bin/env bash
set -euo pipefail

# Stop the telemetry-stream API server and any related background processes.
# Usage: ./scripts/stop.sh
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${REPO_DIR}/.run/backend.pid" ]]; then
  PID="$(cat "${REPO_DIR}/.run/backend.pid")"
  if kill -0 "${PID}" 2>/dev/null; then
    echo "Stopping API server (PID ${PID})..."
    kill "${PID}" 2>/dev/null || true
    sleep 1
    kill -9 "${PID}" 2>/dev/null || true
    echo "Stopped."
  else
    echo "No running server (stale PID file)."
  fi
  rm -f "${REPO_DIR}/.run/backend.pid"
else
  echo "No PID file found. Checking for stray processes..."
  pkill -f "telemetry.serve server" 2>/dev/null || echo "No stray processes found."
fi

rm -f "${REPO_DIR}/.run/backend.log"
