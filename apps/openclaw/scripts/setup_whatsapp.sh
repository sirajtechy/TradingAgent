#!/usr/bin/env bash
# MyTradingSpace + OpenClaw WhatsApp (scan QR on Mac, chat from phone).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== MyTradingSpace WhatsApp setup ==="
echo "Repo: ${ROOT}"
echo ""

# Ensure workspace, skills, ollama/qwen3.6, Polygon env
"${SCRIPT_DIR}/setup_phone_dryrun.sh"

export ROOT
"${ROOT}/.venv/bin/python" <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
config_path = Path.home() / ".openclaw" / "openclaw.json"

with config_path.open(encoding="utf-8") as f:
    cfg = json.load(f)

cfg.setdefault("plugins", {}).setdefault("entries", {})["whatsapp"] = {"enabled": True}

channels = cfg.setdefault("channels", {})
channels["whatsapp"] = {
    "dmPolicy": "pairing",
    "groupPolicy": "allowlist",
    "groups": {"*": {"requireMention": True}},
}

with config_path.open("w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print(f"Updated {config_path} (channels.whatsapp dmPolicy=pairing)")
PY

chmod +x "${SCRIPT_DIR}"/*.sh

echo ""
echo "Restarting gateway..."
openclaw gateway restart 2>&1 || true

echo ""
openclaw channels status 2>&1 | grep -i whatsapp || true
if ! openclaw channels status 2>&1 | grep -qi 'connected'; then
  echo ""
  echo "Not connected yet. Link with:"
  echo "  openclaw channels login --channel whatsapp"
fi

echo ""
cat <<'EOF'
=== First message from phone ===

4) From your phone, send yourself (Saved Messages) OR message the linked number:

     Analyze AAPL as of 2026-05-15 with phoenix-fa

5) On Mac, approve pairing (first DM only):

     openclaw pairing list whatsapp
     openclaw pairing approve whatsapp <CODE>

=== Dry-run prompts ===

  • Single ticker:  Analyze NVDA as of 2026-05-15 phoenix-fa
  • Full pilot:     Run today's sector backtest
  • New session:    /new

Model: ollama/qwen3.6:latest (first reply may take 1–3 min).

=== Tips ===

  • Mac must stay awake; gateway must run (LaunchAgent: ai.openclaw.gateway).
  • Dedicated WhatsApp number is cleaner than personal; personal works with pairing.
  • Groups: mention the bot (@) — groups are allowlist by default.

EOF
