#!/usr/bin/env bash
# Install / refresh OpenClaw gateway for 24/7 operation (WhatsApp + agent exec).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== OpenClaw 24/7 gateway setup ==="
echo "Repo: ${ROOT}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI not found. Install from https://documentation.openclaw.ai" >&2
  exit 1
fi

# Stop stale gateway if port is held
openclaw gateway stop 2>/dev/null || true

openclaw doctor --fix 2>/dev/null || openclaw doctor || true

echo "--- installing gateway LaunchAgent ---"
openclaw gateway install

echo "--- enabling gateway ---"
openclaw gateway start 2>/dev/null || openclaw gateway install

echo ""
echo "Gateway should run 24/7 via LaunchAgent (ai.openclaw.gateway)."
echo "Dashboard: openclaw dashboard  (http://127.0.0.1:18789/)"
echo "Status:    openclaw gateway status"
echo ""
echo "Daily backtest (no LLM): ${ROOT}/openclaw/scripts/install_daily_launchd.sh"
echo "Test analyze: ${ROOT}/openclaw/scripts/orchestrator_analyze.sh --ticker AAPL --date 2026-05-15"
