#!/usr/bin/env bash
# Register OpenClaw cron jobs (requires gateway + openclaw CLI).
# Primary automation should use install_daily_launchd.sh (no LLM cost).
# This adds an optional morning agent job that can re-announce results to Telegram.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CRON_EXPR="${CRON_EXPR:-30 7 * * 1-5}"
CRON_TZ="${CRON_TZ:-America/New_York}"
TELEGRAM_TO="${TELEGRAM_CHAT_ID:-}"
CHANNEL="${CRON_CHANNEL:-telegram}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI not found" >&2
  exit 1
fi

PIPELINE="${ROOT}/openclaw/scripts/run_daily_pipeline.sh"
MSG="Run this shell command exactly (use exec tool), then summarize stdout for the user:
${PIPELINE}

If master_pilot was written, mention signal_date, BUY count, path to unified_master JSON, and any errors."

ARGS=(
  --name "MyTradingSpace daily pipeline (agent)"
  --cron "${CRON_EXPR}"
  --tz "${CRON_TZ}"
  --session isolated
  --message "${MSG}"
  --tools exec,read
  --timeout-seconds 3600
  --announce
  --channel "${CHANNEL}"
)

if [[ -n "${TELEGRAM_TO}" ]]; then
  ARGS+=(--to "${TELEGRAM_TO}")
fi

echo "Adding OpenClaw cron job..."
openclaw cron add "${ARGS[@]}"
echo "Done. List jobs: openclaw cron list"
echo "Tip: prefer launchd for the heavy pilot; use this only if you want agent narration."
