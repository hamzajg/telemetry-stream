#!/usr/bin/env bash
set -euo pipefail

# Send sample telemetry events to the running API server.
# Usage: ./scripts/run_producer.sh [COUNT] [DELAY_SEC] [BASE_URL]
COUNT="${1:-5}"
DELAY="${2:-1.0}"
BASE_URL="${3:-http://127.0.0.1:8000}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Sending ${COUNT} telemetry events to ${BASE_URL}..."
cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}/src"
python -m telemetry.serve producer --count "${COUNT}" --delay "${DELAY}" --base-url "${BASE_URL}"
