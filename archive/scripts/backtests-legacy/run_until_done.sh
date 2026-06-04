#!/usr/bin/env bash
# Loop Phoenix+Fund 2025 backtest with --resume until the workbook is produced.
#
# Typical use (leave running in Terminal / tmux until finished):
#
#   ./scripts/backtests/run_until_done.sh
#
# Options:
#   -o,--output-dir   Output directory (relative to repo root or absolute).
#                     Default: data/output/backtests/phoenix_fund_orchestrator_2025_large
#   -w,--workers      Thread pool size (default: 4)
#   -t,--tickers       --total-tickers (default: 150)
#   -s,--sleep         Seconds between attempts if incomplete (default: 120)
#   -m,--max-runs      Max python invocations (default: 200; avoids infinite loops)
#   -p,--period-workers Parallel month evaluations inside each ticker (default: 10)
#
# Override venv location if needed:
#   VENV=/path/to/.venv/bin/activate ./scripts/backtests/run_until_done.sh

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

OUTPUT_REL="data/output/backtests/phoenix_fund_orchestrator_2025_large"
WORKERS=4
TOTAL_TICKERS=150
SLEEP_BETWEEN=120
MAX_RUNS=200
PERIOD_WORKERS=10

usage() {
  sed -n '1,25p' "$0"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage ;;
    -o | --output-dir)
      OUTPUT_REL="$2"
      shift 2
      ;;
    -w | --workers)
      WORKERS="$2"
      shift 2
      ;;
    -t | --tickers)
      TOTAL_TICKERS="$2"
      shift 2
      ;;
    -s | --sleep)
      SLEEP_BETWEEN="$2"
      shift 2
      ;;
    -m | --max-runs)
      MAX_RUNS="$2"
      shift 2
      ;;
    -p | --period-workers)
      PERIOD_WORKERS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage 1
      ;;
  esac
done

cd "${PROJECT_ROOT}" || exit 1

if [[ "${OUTPUT_REL}" = /* ]]; then
  OUT_ABS="${OUTPUT_REL}"
else
  mkdir -p "${OUTPUT_REL}"
  OUT_ABS="$(cd "${OUTPUT_REL}" && pwd)"
fi

mkdir -p "${OUT_ABS}"

VENV_ACTIVATE="${VENV:-${PROJECT_ROOT}/../.venv/bin/activate}"
if [[ ! -f "${VENV_ACTIVATE}" ]]; then
  echo "ERROR: Activate script not found: ${VENV_ACTIVATE}" >&2
  echo "Set VENV=/path/to/.venv/bin/activate" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${VENV_ACTIVATE}"

XLSX="${OUT_ABS}/phoenix_fund_orchestrator_backtest_2025.xlsx"
LOG="${OUT_ABS}/run_until_done.log"
PY=("python" "${PROJECT_ROOT}/scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py"
    "--executor" "thread"
    "--workers" "${WORKERS}"
    "--period-workers" "${PERIOD_WORKERS}"
    "--total-tickers" "${TOTAL_TICKERS}"
    "--output-dir" "${OUT_ABS}"
    "--resume")

if [[ -f "${XLSX}" ]]; then
  echo "Already complete: ${XLSX}"
  exit 0
fi

run_num=1
while [[ ${run_num} -le ${MAX_RUNS} ]]; do
  {
    echo ""
    echo "================================================================"
    echo "run_until_done: attempt ${run_num}/${MAX_RUNS} ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
    echo "command: PYTHONUNBUFFERED=1 ${PY[*]}"
    echo "================================================================"
  } | tee -a "${LOG}"

  PYTHONUNBUFFERED=1 "${PY[@]}" 2>&1 | tee -a "${LOG}"
  rc=${PIPESTATUS[0]}

  if [[ -f "${XLSX}" ]]; then
    {
      echo ""
      echo "run_until_done: SUCCESS — ${XLSX}"
      echo "python exit code was: ${rc}"
    } | tee -a "${LOG}"
    exit 0
  fi

  echo "" | tee -a "${LOG}"
  echo "run_until_done: no workbook yet (python exit=${rc}); sleeping ${SLEEP_BETWEEN}s before retry…" | tee -a "${LOG}"
  sleep "${SLEEP_BETWEEN}"
  run_num=$((run_num + 1))
done

echo "run_until_done: gave up after ${MAX_RUNS} attempts (still no ${XLSX})" | tee -a "${LOG}"
exit 1
