# MyTradingSpace — Multi-Agent Stock Analysis Platform

A **deterministic, rule-based** halal-universe screening stack: **Phoenix** (pattern/stage TA) + **Fundamental** analysis fused via orchestrator **CWAF** (default **90% Phoenix / 10% FA**). Outputs feed `master_pilot.json` backtests and the **Research Lab** dashboard at http://localhost:3055.

**Control plane:** `./bin/mts` — one entry for dashboard, backtests, analyze, export, and daily ops.

**Operator journals:** [Trading-Journals/](./Trading-Journals/) — daily commands cheat sheet + full project journal.

---

## Quick Start

```bash
cd MyTradingSpace
cp .env.example .env          # POLYGON_API_KEY required; FMP optional for fundamentals
python3 -m pip install -e .
cd apps/backtest-dashboard && npm install && cd ../..

set -a && source .env && set +a

# Demo: backtest all sectors + dashboard
./bin/mts lab unified

# Open Research Lab
#   http://localhost:3055/research/phoenix   — BUY/WATCH + "Already up" extension column
#   http://localhost:3055/research/runs
#   http://localhost:3055/research/signals
```

---

## Daily workflow

See **[Trading-Journals/DailyCommands.txt](./Trading-Journals/DailyCommands.txt)** for the full ship-it list.

```bash
set -a && source .env && set +a

./bin/mts daily                 # unified backtest + BUY excel + notify
./bin/mts export                # reconciled BUY/WATCH → Excel + JSON
./bin/mts dashboard -b          # Research Lab (background)
./bin/mts stop                  # when done
```

---

## Commands (`bin/mts`)

| Command | Purpose |
|---------|---------|
| `./bin/mts dashboard` | Start dashboard (dev mode, foreground) |
| `./bin/mts dashboard -b` | Start dashboard in background (production build) |
| `./bin/mts stop` | Stop background dashboard on port 3055 |
| `./bin/mts analyze --ticker AAPL --date YYYY-MM-DD` | Single-ticker Phoenix+FA JSON (`--fusion phoenix-fa\|phoenix\|fundamental`) |
| `./bin/mts sector --sector "Information Technology" --date YYYY-MM-DD` | Single-sector pilot (~50 tickers) |
| `./bin/mts unified --date YYYY-MM-DD` | All-sector unified pilot |
| `./bin/mts lab unified --date YYYY-MM-DD` | Unified backtest + start dashboard |
| `./bin/mts lab sector --sector "Energy" --date YYYY-MM-DD` | Sector backtest + dashboard |
| `./bin/mts daily` | Daily pipeline (unified + BUY excel + notify) |
| `./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD` | Reconcile BUY/WATCH signals |

**Defaults**

- `--date` = yesterday (today for `daily`); override globally: `./bin/mts --date 2026-06-03 unified`
- `--eval-days` = **15** calendar days for forward target-hit labeling (TP/FP); use `--eval-days 30` to compare

**Halal sector names** (exact strings for `--sector`): Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities.

---

## Research Lab dashboard

Next.js app: `apps/backtest-dashboard/`

| Route | Purpose |
|-------|---------|
| `/research` | Research Lab hub |
| `/research/phoenix` | `master_pilot.json` viewer — BUY/WATCH, TP/FP, **Already up** extension, Trade focus filter |
| `/research/runs` | Browse all runs |
| `/research/signals` | Reconciled BUY/WATCH export |
| `/research/scans` | Phoenix sector scans |

**Phoenix page (`/research/phoenix`)**

- Select newest **`unified_master_<date>/master_pilot.json`** in the Run dropdown.
- **Already up** — how far price moved *before* the signal (no future data): all **BUY**; **WATCH** when Phoenix score > 60.
- **Trade focus** filter — BUY + WATCH with score > 60.
- **Upside T1/T2** — required % move to reach targets (not realized rally).

Re-run backtests after code updates to populate extension fields in `master_pilot.json`.

---

## Production agents

| Agent | Role |
|-------|------|
| **Phoenix** | Pattern/stage scoring, entry/stop/targets, extension guardrail |
| **Fundamental** | Financial scoring (FMP / yfinance) |
| **Orchestrator** | Phoenix+FA CWAF fusion (`phoenix-fa`) |
| **polygon_data** | Shared Polygon client |

Legacy agents (`technical`, `oneil`, `prediction`, ta-fa orchestrator) live under **`archive/agents/`** — not used in daily production.

---

## Project structure

```
MyTradingSpace/
├── bin/mts                  # Control plane CLI
├── cli/                     # CLI implementation
├── pipelines/               # analyze, sector, unified, daily, backtest
├── agents/
│   ├── phoenix/             # Pattern/stage + extension guardrail
│   ├── fundamental/
│   ├── orchestrator/        # Phoenix+FA fusion
│   └── polygon_data/
├── core/                    # universe, export, contracts, paths
├── scripts/backtests/       # Sector + unified pilot engines
├── apps/
│   ├── backtest-dashboard/  # Research Lab UI
│   └── openclaw/            # Phone / WhatsApp wrappers
├── Trading-Journals/        # DailyCommands + DailyTradingJournal (operator notes)
├── docs/                    # Specs, architecture, SCRIPTS.md
├── data/input/              # Halal universe, master tickers
├── data/output/             # trading_runs (gitignored)
└── archive/                 # Retired code
```

---

## Output locations

| Path | Contents |
|------|----------|
| `data/output/trading_runs/unified_master_<date>/master_pilot.json` | All-sector backtest |
| `data/output/trading_runs/sector_<slug>_<date>/master_pilot.json` | Single-sector backtest |
| `data/output/trading_runs/phoenix_signals_reconciled.xlsx` | Export BUY/WATCH |
| `data/output/trading_runs/phoenix_buy_<date>.xlsx` | Daily BUY export |

All run outputs are **gitignored**.

---

## Documentation

| Resource | Contents |
|----------|----------|
| [Trading-Journals/DailyCommands.txt](./Trading-Journals/DailyCommands.txt) | Daily operator commands |
| [Trading-Journals/DailyTradingJournal.txt](./Trading-Journals/DailyTradingJournal.txt) | Full backtest matrix + change log |
| [docs/SCRIPTS.md](./docs/SCRIPTS.md) | All scripts and engines |
| [docs/STRUCTURE.md](./docs/STRUCTURE.md) | Folder layout |
| [docs/architecture/CONFIG.md](./docs/architecture/CONFIG.md) | CLI flags reference |

---

## Environment

```bash
python3 -m pip install -e .
export POLYGON_API_KEY=your_key    # or in .env
export FMP_API_KEY=your_key        # optional; yfinance fallback for FA
cd apps/backtest-dashboard && npm install
```

---

## License

Project-specific license and maintainer notes live with the upstream repository settings.
