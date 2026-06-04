# OpenClaw integration for MyTradingSpace

Self-contained OpenClaw scaffold. **Does not modify** `agents/` — only adds wrappers, skills, and example config.

## Architecture

```
You → OpenClaw (trading-orchestrator) → openclaw/scripts/orchestrator_analyze.sh
       → Phoenix + Fundamental + fuse_by_mode (phoenix-fa)
```

Production Python path: `scripts/run_trading.py analyze --fusion phoenix-fa` (same logic as the wrapper).

**Do not** use `agents/orchestrator/service.py` for Phoenix workflows — that is **TA+FA** only.

## Quick setup

### 1. Install OpenClaw

Follow [OpenClaw docs](https://documentation.openclaw.ai/gateway/configuration): install CLI, then:

```bash
openclaw onboard
# or: openclaw configure
```

### 2. Copy config

```bash
cp openclaw/config/openclaw.example.json5 ~/.openclaw/openclaw.json
```

Edit `~/.openclaw/openclaw.json`: replace every `ABS_PATH` with your absolute path to **MyTradingSpace** (parent of `openclaw/`).

### 3. Secrets

```bash
cp openclaw/.env.example ~/.openclaw/.env
chmod 600 ~/.openclaw/.env
# Set POLYGON_API_KEY, FMP_API_KEY (if using fmp)
```

### 4. Python environment

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Validate & start

```bash
openclaw doctor
openclaw gateway
# Control UI: http://127.0.0.1:18789/
```

New session: `/new` in chat, then:

```bash
openclaw skills list   # should include trading-orchestrator
```

### 6. Smoke test (no OpenClaw)

```bash
cd /path/to/MyTradingSpace
chmod +x openclaw/scripts/orchestrator_analyze.sh
.venv/bin/python openclaw/scripts/orchestrator_analyze.py --ticker AAPL --date 2026-05-14 --fusion phoenix-fa
```

### 7. Smoke test (OpenClaw)

```bash
openclaw agent --message "Analyze AAPL as of 2026-05-14 with phoenix-fa"
```

## Layout

| Path | Purpose |
|------|---------|
| `scripts/orchestrator_analyze.py` | Thin wrapper → `pipelines.analyze` |
| `scripts/orchestrator_analyze.sh` | Shell entry for `exec` tool |
| `scripts/install_gateway_24_7.sh` | Gateway LaunchAgent for 24/7 WhatsApp |
| `scripts/run_daily_pipeline.sh` | → `python -m pipelines daily` |
| `config/openclaw.example.json5` | Example gateway config |
| `workspace/AGENTS.md`, `TOOLS.md` | Agent instructions |
| `workspace/skills/*/SKILL.md` | OpenClaw skills |

## Skills

| Skill | When |
|-------|------|
| `trading-orchestrator` | Default — phoenix-fa fusion |
| `daily-unified-pilot` | All-sector master pilot + BUY excel |
| `sector-pilot` | Single-sector backtest (e.g. Energy) |
| `phoenix-only` | Debug Phoenix alone |
| `fundamental-only` | Debug Fundamental alone |

Agnostic CLI (same backends): `python -m pipelines analyze|sector|unified|daily` from repo root.

## Optional: symlink workspace

Instead of editing `workspace` path in config:

```bash
ln -sf /path/to/MyTradingSpace/openclaw/workspace ~/.openclaw/workspace-trading
```

Then set `agents.defaults.workspace` to `~/.openclaw/workspace-trading`.

---

## Remote / pre-market automation (phone + laptop away)

### Reality check

- **Mac asleep or lid closed** → nothing runs. Use an **always-on Mac** (mini / home server) or **prevent sleep** when plugged in.
- **OpenClaw gateway** must stay running on that machine for phone chat.
- Use **Tailscale** (recommended) to reach `http://<tailscale-ip>:18789` — do not expose the gateway on the public internet.

### What runs daily

`openclaw/scripts/run_daily_pipeline.sh`:

1. **All-sector unified pilot** → `data/output/trading_runs/unified_master_<date>/master_pilot.json`
2. **Phoenix BUY excel** for that date only
3. **Telegram summary** (if `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in env)

### One-time setup

```bash
# 1. Secrets on the always-on Mac
cp openclaw/.env.example ~/.openclaw/.env
cp .env.example .env   # or symlink — POLYGON_API_KEY required
chmod 600 ~/.openclaw/.env

# 2. Telegram: create bot via @BotFather, get chat id via @userinfobot
#    Put token + chat id in ~/.openclaw/.env

# 3. OpenClaw config (Telegram + skills)
cp openclaw/config/openclaw.example.json5 ~/.openclaw/openclaw.json

# 4. 24/7 gateway (WhatsApp / phone control)
chmod +x openclaw/scripts/install_gateway_24_7.sh
./openclaw/scripts/install_gateway_24_7.sh
# Edit ABS_PATH, botToken, allowFrom

# 4. Schedule without LLM (recommended) — macOS LaunchAgent 06:30 local
chmod +x openclaw/scripts/*.sh
./openclaw/scripts/install_daily_launchd.sh

# 5. Gateway (keep running — launchd or tmux)
openclaw gateway
```

### Phone usage

| Action | How |
|--------|-----|
| Chat: analyze one ticker | Telegram → "Analyze AAPL as of today phoenix-fa" |
| Chat: run today's full pilot | "Run today's sector backtest" / `daily-unified-pilot` |
| Auto pre-market | LaunchAgent at 06:30 → Telegram summary when done |
| Dashboard | Tailscale → `http://<host>:3055` (if `npm run start` is running) |

---

## WhatsApp setup (phone control)

WhatsApp is already enabled in your OpenClaw install; you only need to **link** it once.

### One command (config + gateway)

```bash
cd /path/to/MyTradingSpace
./openclaw/scripts/setup_whatsapp.sh
```

### Link with QR (interactive — Mac terminal)

```bash
openclaw channels login --channel whatsapp
```

On your phone: **WhatsApp → Settings → Linked devices → Link a device** → scan the QR.

Check status:

```bash
openclaw channels status
```

### First message + pairing

1. From your phone, send (to the linked chat / Saved Messages):

   `Analyze AAPL as of 2026-05-15 with phoenix-fa`

2. On the Mac:

```bash
openclaw pairing list whatsapp
openclaw pairing approve whatsapp <CODE>
```

### Example prompts

| Goal | WhatsApp message |
|------|------------------|
| Single ticker | `Analyze AAPL as of 2026-05-15 phoenix-fa` |
| Today's full pilot | `Run today's sector backtest` |
| Reset context | `/new` |

**Model:** `ollama/qwen3.6:latest` — first reply can take 1–3 minutes.

**Requirements:** Mac awake, Ollama running (`ollama serve`), gateway running (`openclaw gateway` or LaunchAgent `ai.openclaw.gateway`).

### Optional OpenClaw cron (agent + announce)

Uses LLM tokens. Prefer LaunchAgent for the heavy job.

```bash
export TELEGRAM_CHAT_ID=123456789
./openclaw/scripts/install_daily_openclaw_cron.sh
```

### Manual test

```bash
./openclaw/scripts/run_daily_pipeline.sh
# Or pilot only:
SIGNAL_DATE=$(date +%Y-%m-%d) ./openclaw/scripts/run_daily_unified_pilot.sh
```

### Logs

| File | Purpose |
|------|---------|
| `data/output/trading_runs/logs/daily_pipeline_<date>.log` | Full pipeline |
| `data/output/trading_runs/logs/unified_pilot_<date>.log` | Pilot only |
| `data/output/trading_runs/logs/launchd-daily-pilot.log` | launchd stdout |

### Layout (automation)

| Path | Purpose |
|------|---------|
| `scripts/run_daily_pipeline.sh` | Pilot + BUY excel + Telegram |
| `scripts/run_daily_unified_pilot.sh` | Pilot only |
| `scripts/notify_daily_summary.py` | Summary + Telegram API |
| `scripts/install_daily_launchd.sh` | Install 06:30 LaunchAgent |
| `scripts/install_daily_openclaw_cron.sh` | Optional OpenClaw cron |
| `launchd/com.mytrading.daily-pilot.plist.example` | Schedule template |
| `workspace/skills/daily-unified-pilot/` | Phone: "run today's backtest" |
