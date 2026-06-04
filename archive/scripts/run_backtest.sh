#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_backtest.sh — Run the full halal predictions batch and print a summary.
#
# Usage:
#   ./run_backtest.sh                    # today's date, 20-day horizon, 3 workers
#   ./run_backtest.sh --date 2026-04-04  # specific cutoff date
#   ./run_backtest.sh --workers 5        # more parallelism
#   ./run_backtest.sh --target-days 15   # shorter horizon
#   ./run_backtest.sh --sector "Information Technology"  # single sector
#
# All flags are forwarded straight to run_halal_predictions.py.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${REPO_DIR}/../.venv/bin/python3"
SCRIPT="${REPO_DIR}/scripts/run_halal_predictions.py"
LOG="/tmp/halal_backtest_$(date +%Y%m%d_%H%M%S).log"

# ── Defaults (override via flags) ────────────────────────────────────────────
DATE_ARG="--date $(date +%Y-%m-%d)"
WORKERS="--workers 3"
TARGET_DAYS="--target-days 20"
EXTRA_ARGS=""

# ── Parse args passed to this script ─────────────────────────────────────────
FORWARD_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date) DATE_ARG="--date $2"; shift 2 ;;
        --workers) WORKERS="--workers $2"; shift 2 ;;
        --target-days) TARGET_DAYS="--target-days $2"; shift 2 ;;
        *) FORWARD_ARGS+=("$1"); shift ;;
    esac
done

ALL_ARGS="$DATE_ARG $WORKERS $TARGET_DAYS ${FORWARD_ARGS[*]+"${FORWARD_ARGS[@]}"}"

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              HALAL PREDICTIONS BACKTEST RUNNER               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Args    : $ALL_ARGS"
echo "  Log     : $LOG"
echo "  Started : $(date '+%Y-%m-%d %H:%M:%S')"
echo "──────────────────────────────────────────────────────────────"
echo ""

# ── Run ──────────────────────────────────────────────────────────────────────
START_TS=$(date +%s)

"$PYTHON" "$SCRIPT" $ALL_ARGS 2>&1 | tee "$LOG"

EXIT_CODE=${PIPESTATUS[0]}
END_TS=$(date +%s)
ELAPSED=$(( END_TS - START_TS ))
MINS=$(( ELAPSED / 60 ))
SECS=$(( ELAPSED % 60 ))

echo ""
echo "──────────────────────────────────────────────────────────────"
echo "  Finished : $(date '+%Y-%m-%d %H:%M:%S')  (${MINS}m ${SECS}s)"

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "  Status   : ❌ FAILED (exit $EXIT_CODE)"
    echo ""
    echo "  Last 20 lines of log:"
    tail -20 "$LOG"
    exit $EXIT_CODE
fi

# ── Parse output JSON summary ─────────────────────────────────────────────────
CUTOFF_DATE=$(echo "$DATE_ARG" | awk '{print $2}')
SUMMARY_JSON="${REPO_DIR}/data/output/predictions/halal_${CUTOFF_DATE}_summary.json"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                        RESULTS SUMMARY                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"

if [[ -f "$SUMMARY_JSON" ]]; then
    "$PYTHON" - <<PYEOF
import json

with open("$SUMMARY_JSON") as f:
    s = json.load(f)

meta   = s.get("run_meta", {})
trades = s.get("trades", [])
errors = s.get("errors", 0) if isinstance(s.get("errors"), int) else len(s.get("errors", []))

total    = meta.get("total", 0)
n_trades = meta.get("trades", len(trades))
no_trade = meta.get("no_trades", 0)
elapsed  = meta.get("elapsed_sec", 0)

bullish  = sum(1 for t in trades if t.get("sentiment") == "bullish")
neutral  = sum(1 for t in trades if t.get("sentiment") == "neutral")
bearish  = sum(1 for t in trades if t.get("sentiment") == "bearish")
conflict = sum(1 for t in trades if t.get("conflict"))
avg_score = sum(t.get("confidence_score", 0) for t in trades) / len(trades) if trades else 0

print(f"  Date      : {meta.get('cutoff_date','?')}")
print(f"  Tickers   : {total}")
print(f"  Horizon   : {meta.get('target_days','?')} trading days")
print(f"  Runtime   : {elapsed/60:.1f} min")
print("")
print(f"  Trades    : {n_trades}")
print(f"  No-trade  : {no_trade}")
print(f"  Errors    : {errors}")
print(f"  Bullish   : {bullish}  Bearish: {bearish}  Neutral: {neutral}")
print(f"  Conflicts : {conflict}")
print(f"  Avg Score : {avg_score:.1f}")
print("")
print("  ── Top 10 Trades (by confidence score) ────────────────────")
print(f"  {'Ticker':<8} {'Pattern/Source':<24} {'Score':>6}  {'Tech':>5}  {'Fund':>5}  RR")
print(f"  {'─'*8} {'─'*24} {'─'*6}  {'─'*5}  {'─'*5}  ──")
top = sorted(trades, key=lambda x: x.get("confidence_score", 0), reverse=True)[:10]
for t in top:
    ticker  = t.get("ticker", "?")
    src     = (t.get("entry_source") or "N/A")[:24]
    score   = t.get("confidence_score", 0)
    tech    = t.get("tech_score", 0)
    fund    = t.get("fund_score", 0)
    rr      = t.get("reward_risk_ratio") or 0
    print(f"  {ticker:<8} {src:<24} {score:>6.1f}  {tech:>5.1f}  {fund:>5.1f}  {rr:.1f}")
PYEOF
else
    # Fallback: count files directly
    OUTPUT_DIR="${REPO_DIR}/data/output/predictions/halal_${CUTOFF_DATE}"
    if [[ -d "$OUTPUT_DIR" ]]; then
        TOTAL=$(ls "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
        TRADES=$("$PYTHON" -c "
import json, glob
files = glob.glob('${OUTPUT_DIR}/*.json')
print(sum(1 for f in files if json.load(open(f)).get('trade')))
")
        NO_TRADE=$(( TOTAL - TRADES ))
        echo "  Total files : $TOTAL"
        echo "  Trades      : $TRADES"
        echo "  No-trade    : $NO_TRADE"
    else
        echo "  No output found at $OUTPUT_DIR"
    fi
fi

echo ""
echo "  Full log saved to: $LOG"
echo "──────────────────────────────────────────────────────────────"
echo ""
