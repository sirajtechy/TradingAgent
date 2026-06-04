# MyTradingSpace — Multi-Agent Stock Analysis Platform

A **deterministic, rule-based** multi-agent stack for point-in-time stock analysis, halal-universe screening, Phoenix-style pattern scoring, and **Confidence-Weighted Asymmetric Fusion (CWAF)**. Outputs feed **JSON run bundles**, **backtests**, and a **Next.js Research Lab dashboard**.

---

## Quick Start

```bash
# Start dashboard
./bin/mts dashboard                     # → http://localhost:3055

# Run backtests
./bin/mts unified --date 2026-05-28     # All-sector unified pilot
./bin/mts sector --sector Energy        # Single sector
./bin/mts analyze --ticker AAPL         # Single ticker

# Export signals
./bin/mts export --from 2026-05-10 --to 2026-05-28

# Full daily pipeline
./bin/mts daily

# Combined: backtest + dashboard
./bin/mts lab unified --date 2026-05-28
```

---

## Project Structure

```
MyTradingSpace/
├── bin/mts                  # Control plane (dashboard, analyze, sector, unified, daily, export, lab)
├── cli/                     # CLI implementation
├── pipelines/               # Pipeline modules (analyze, sector, unified, daily)
├── agents/                  # Agent packages
│   ├── phoenix/             # Phoenix pattern/stage scoring
│   ├── technical/           # Technical analysis (Polygon OHLCV)
│   ├── fundamental/         # Fundamental analysis (FMP)
│   ├── orchestrator/        # Fusion logic (TA+FA, Phoenix+FA)
│   └── polygon_data/        # Shared Polygon client
├── core/                    # Core modules
│   ├── universe/            # Stock universes, halal sectors
│   ├── data/                # Data access (polygon re-export)
│   ├── io/                  # Export, master_pilot merge
│   └── contracts/           # Fusion, envelope contracts
├── apps/
│   ├── backtest-dashboard/  # Next.js Research Lab UI
│   └── openclaw/            # WhatsApp / phone automation
├── data/
│   ├── input/               # Master data, halal universe
│   └── output/              # Trading runs, exports (gitignored)
├── docs/                    # All documentation
├── backtests/common.py      # Universe constants shim → core/universe
└── archive/                 # Retired scripts and tests
```

---

## Documentation

All documentation lives in `docs/`:

| Folder | Contents |
|--------|----------|
| `docs/` | Main docs (SCRIPTS, CHANGELOG, STRUCTURE, MODULE_MAP) |
| `docs/specs/` | Agent specs, ADRs, pipeline design |
| `docs/plans/` | Production plan, refactor plan |
| `docs/agent-learning/` | Steering guides, backtesting guides |
| `docs/strategies/` | Trading strategies |
| `docs/prompts/` | Agent prompts |

Key files:
- **`docs/SCRIPTS.md`** — All commands and scripts
- **`docs/MODULE_MAP.md`** — Feature → module mapping
- **`docs/STRUCTURE.md`** — Folder layout
- **`docs/specs/ORCHESTRATOR_MODES.md`** — Fusion modes (phoenix-fa, ta-fa)

---

## Commands (`bin/mts`)

| Command | Purpose |
|---------|---------|
| `./bin/mts dashboard` | Start dashboard on http://localhost:3055 |
| `./bin/mts stop` | Stop dashboard |
| `./bin/mts analyze --ticker AAPL --date YYYY-MM-DD` | Single-ticker analysis |
| `./bin/mts sector --sector Energy --date YYYY-MM-DD` | Single-sector pilot |
| `./bin/mts unified --date YYYY-MM-DD` | All-sector unified pilot |
| `./bin/mts daily` | Daily pipeline (unified + export + notify) |
| `./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD` | Reconcile BUY+WATCH → Excel + JSON |
| `./bin/mts lab unified --date YYYY-MM-DD` | Backtest + dashboard together |

---

## Dashboard (Research Lab)

Next.js app at `apps/backtest-dashboard/`:

| Route | Purpose |
|-------|---------|
| `/` | Home / navigation |
| `/research` | Research Lab hub |
| `/research/signals` | Reconciled BUY/WATCH signals |
| `/research/phoenix` | Single master_pilot viewer |
| `/research/runs` | Trading runs browser |
| `/research/scans` | Phoenix sector scans |

---

## Agents

| Agent | Purpose |
|-------|---------|
| **Phoenix** | Stage/pattern/risk scoring, trade-level hints |
| **Technical** | Momentum, trend, pattern rules (Polygon OHLCV) |
| **Fundamental** | Financial health, valuation, quality (FMP) |
| **Orchestrator** | Fusion: TA+FA (`ta-fa`) or Phoenix+FA (`phoenix-fa`, default 90/10 weights) |

---

## Environment Setup

```bash
# Python venv
python -m venv .venv && source .venv/bin/activate
pip install -e .

# API keys
export FMP_API_KEY=your_key
export POLYGON_API_KEY=your_key

# Dashboard
cd apps/backtest-dashboard && npm install
```

---

## Output Locations

| Path | Contents |
|------|----------|
| `data/output/trading_runs/` | master_pilot.json, run_bundle.json |
| `data/output/trading_runs/phoenix_signals_reconciled.xlsx` | Exported BUY/WATCH signals |
| `data/archive/trading_runs/` | Archived runs |

All output directories are **gitignored**.

---

## License

Project-specific license and maintainer notes live with the upstream repository settings.
