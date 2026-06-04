#!/usr/bin/env bash
# Run all-sector unified master_pilot.json for SIGNAL_DATE (default: today).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PY="${MYTRADING_PYTHON:-${ROOT}/.venv/bin/python}"
LOG_DIR="${ROOT}/data/output/trading_runs/logs"
mkdir -p "${LOG_DIR}"

SIGNAL_DATE="${SIGNAL_DATE:-$(date +%Y-%m-%d)}"
EVAL_DAYS="${EVAL_DAYS:-30}"
SECTOR_JOBS="${SECTOR_JOBS:-11}"
WORKERS="${WORKERS:-8}"
PERIOD_WORKERS="${PERIOD_WORKERS:-2}"
LOG_FILE="${LOG_DIR}/unified_pilot_${SIGNAL_DATE}.log"

if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3)"
fi

cd "${ROOT}"
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

echo "=== MyTradingSpace daily unified pilot ===" | tee "${LOG_FILE}"
echo "signal_date=${SIGNAL_DATE} eval_days=${EVAL_DAYS}" | tee -a "${LOG_FILE}"
echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${LOG_FILE}"

"${PY}" -m pipelines unified \
  --signal-date "${SIGNAL_DATE}" \
  --eval-days "${EVAL_DAYS}" \
  --sector-jobs "${SECTOR_JOBS}" \
  --workers "${WORKERS}" \
  --period-workers "${PERIOD_WORKERS}" \
  2>&1 | tee -a "${LOG_FILE}"

MERGED="${ROOT}/data/output/trading_runs/unified_master_${SIGNAL_DATE}/master_pilot.json"
echo "finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${LOG_FILE}"
echo "MERGED_OUTPUT=${MERGED}"
