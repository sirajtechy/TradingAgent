#!/usr/bin/env bash
# Batch Polygon verification for IT sector sweep — safe to run while backtests are idle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
LOG="${ROOT}/data/output/verify/batch_run.log"
mkdir -p "${ROOT}/data/output/verify"

echo "=== batch start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
export POLYGON_REQUESTS_PER_SECOND=2

"${PY}" scripts/verify/verify_batch.py \
  --glob "sector_information-technology_*" \
  --rate-limit 2 >> "$LOG" 2>&1

echo "=== batch end $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG"
