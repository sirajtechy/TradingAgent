#!/usr/bin/env bash
# Install macOS LaunchAgent for daily pre-market pipeline (no OpenClaw / no LLM).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLIST_SRC="${SCRIPT_DIR}/../launchd/com.mytrading.daily-pilot.plist.example"
PLIST_DST="${HOME}/Library/LaunchAgents/com.mytrading.daily-pilot.plist"

if [[ ! -f "${PLIST_SRC}" ]]; then
  echo "Missing ${PLIST_SRC}" >&2
  exit 1
fi

mkdir -p "${HOME}/Library/LaunchAgents"
sed "s|ABS_PATH|${ROOT}|g" "${PLIST_SRC}" > "${PLIST_DST}"
chmod +x "${ROOT}/openclaw/scripts/run_daily_pipeline.sh"
chmod +x "${ROOT}/openclaw/scripts/run_daily_unified_pilot.sh"

launchctl bootout "gui/$(id -u)/com.mytrading.daily-pilot" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_DST}"
launchctl enable "gui/$(id -u)/com.mytrading.daily-pilot"
launchctl kickstart -k "gui/$(id -u)/com.mytrading.daily-pilot" 2>/dev/null || true

echo "Installed ${PLIST_DST}"
echo "Default schedule: 06:30 local (edit plist Hour/Minute to change)."
echo "Logs: ${ROOT}/data/output/trading_runs/logs/launchd-daily-pilot.log"
echo "Test now: ${ROOT}/openclaw/scripts/run_daily_pipeline.sh"
