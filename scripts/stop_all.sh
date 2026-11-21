#!/usr/bin/env bash
set -euo pipefail

# Stop all services started by run_stack.sh (backend + frontend).
# Usage: ./scripts/stop_all.sh
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Stop frontend
if [[ -f "${REPO_DIR}/.run/frontend.pid" ]]; then
  FPID="$(cat "${REPO_DIR}/.run/frontend.pid")"
  if kill -0 "${FPID}" 2>/dev/null; then
    echo "Stopping frontend dev server (PID ${FPID})..."
    kill "${FPID}" 2>/dev/null || true
    sleep 1
    kill -9 "${FPID}" 2>/dev/null || true
    echo "Frontend stopped."
  fi
  rm -f "${REPO_DIR}/.run/frontend.pid"
fi

# Stop backend (reuses stop.sh)
if [[ -f "${REPO_DIR}/scripts/stop.sh" ]]; then
  "${REPO_DIR}/scripts/stop.sh"
fi

# Clean up log files
rm -f "${REPO_DIR}/.run/frontend.log"

echo "All services stopped."
