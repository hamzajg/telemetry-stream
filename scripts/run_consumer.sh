#!/usr/bin/env bash
set -euo pipefail

# Run the stream consumer: read events from the bus, project device state,
# and write to the local lakehouse.
# Usage: ./scripts/run_consumer.sh [ITERATIONS] [DELAY_SEC] [LAKEHOUSE_ROOT]
ITERATIONS="${1:-10}"
DELAY="${2:-1.0}"
LAKEHOUSE_ROOT="${3:-/tmp/telemetry-lakehouse}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Running consumer (${ITERATIONS} iterations, lakehouse: ${LAKEHOUSE_ROOT})..."
cd "${REPO_DIR}"
export PYTHONPATH="${REPO_DIR}/src"
python -m telemetry.serve consumer --iterations "${ITERATIONS}" --delay "${DELAY}" --lakehouse-root "${LAKEHOUSE_ROOT}"
