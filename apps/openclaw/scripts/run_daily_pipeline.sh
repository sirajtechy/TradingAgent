#!/usr/bin/env bash
# Full pre-market pipeline: unified master pilot + optional BUY excel + Telegram summary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PY="${MYTRADING_PYTHON:-${ROOT}/.venv/bin/python}"

SIGNAL_DATE="${SIGNAL_DATE:-$(date +%Y-%m-%d)}"
EXPORT_BUY="${EXPORT_BUY:-1}"
SEND_TELEGRAM="${SEND_TELEGRAM:-1}"
EVAL_DAYS="${EVAL_DAYS:-30}"

LOG="${ROOT}/data/output/trading_runs/logs/daily_pipeline_${SIGNAL_DATE}.log"
mkdir -p "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

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

ARGS=(--signal-date "${SIGNAL_DATE}" --eval-days "${EVAL_DAYS}")
[[ "${EXPORT_BUY}" != "1" ]] && ARGS+=(--no-export-buy)
[[ "${SEND_TELEGRAM}" != "1" ]] && ARGS+=(--no-telegram)

echo "=== daily pipeline signal_date=${SIGNAL_DATE} ==="
"${PY}" -m pipelines daily "${ARGS[@]}"
echo "=== pipeline done ==="
