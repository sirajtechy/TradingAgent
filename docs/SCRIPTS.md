# Scripts reference

**Start here:** `./bin/mts` — control plane for dashboard, backtests, and analyze.

Run from repo root. Python: `.venv/bin/python` or `source .venv/bin/activate`.

---

## Primary — `./bin/mts` (Phase 1)

| Command | Purpose |
|---------|---------|
| `./bin/mts dashboard` | Start backtest dashboard (http://localhost:3055) |
| `./bin/mts dashboard -b` | Dashboard in background |
| `./bin/mts stop` | Stop background dashboard |
| `./bin/mts sector --sector Energy --date YYYY-MM-DD` | Single-sector pilot |
| `./bin/mts unified --date YYYY-MM-DD` | All-sector unified pilot |
| `./bin/mts lab sector --sector Energy --date YYYY-MM-DD` | Sector backtest + dashboard |
| `./bin/mts lab unified --date YYYY-MM-DD` | Unified backtest + dashboard |
| `./bin/mts analyze --ticker AAPL --date YYYY-MM-DD` | Single-ticker JSON |
| `./bin/mts daily --date YYYY-MM-DD` | Daily pipeline (unified + excel + notify) |
| `./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD` | Reconcile BUY+WATCH → Excel + JSON |
| `./bin/mts export` | Default: last 14 days through yesterday, BUY+WATCH, includes archive |

Export outputs:
- `data/output/trading_runs/phoenix_signals_reconciled.xlsx` (BUY, WATCH, All_Signals, Sources, Reconciliation_Log)
- `data/output/trading_runs/phoenix_signals_reconciled.json` → dashboard `/research/signals`

Default `--date` is **yesterday** (today for `daily`). Override globally: `./bin/mts --date 2026-05-28 unified`

**Parallel workflow:** Terminal 1 → `./bin/mts dashboard` · Terminal 2 → `./bin/mts sector …`

---

## Legacy CLIs (internal / batch)

| Command | Purpose |
|---------|---------|
| `python scripts/run_trading.py analyze …` | Batch tickers, halal sectors, compare |
| `python scripts/run_trading.py backtest --engine <alias> -- …` | Heavy backtest engines |
| `python -m pipelines …` | Same backends as `bin/mts` (used by `cli/`) |

**Fusion modes:** `phoenix-fa` (default production), `phoenix`, `fundamental`, `ta-fa`

**Backtest engine aliases** (`run_trading.py backtest --engine …`):

| Alias | Script |
|-------|--------|
| `halal-orchestrator-2025` | `scripts/backtests/run_halal_orchestrator_backtest_2025.py` |
| `halal-sector-pilot` | `scripts/backtests/run_halal_sector_month_pilot.py` |
| `phoenix-fund-2025` | `scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py` |
| `phoenix-orchestrator-2025` | `scripts/backtests/run_phoenix_orchestrator_backtest_2025.py` |
| `orchestrator-legacy` | `scripts/backtests/run_orchestrator_backtest.py` |
| `sector-legacy` | `scripts/backtests/run_sector_backtest.py` |

**Outputs:** `data/output/trading_runs/` (`master_pilot.json`, `run_bundle.json`, logs, `phoenix_buy_*.xlsx`)

---

## OpenClaw & automation

| Script | Purpose |
|--------|---------|
| `apps/openclaw/scripts/orchestrator_analyze.sh --ticker AAPL --date YYYY-MM-DD` | Phone/exec wrapper → `pipelines analyze` |
| `apps/openclaw/scripts/run_daily_pipeline.sh` | Pre-market: `pipelines daily` |
| `apps/openclaw/scripts/run_daily_unified_pilot.sh` | Unified pilot only |
| `apps/openclaw/scripts/notify_daily_summary.py` | Telegram summary from `master_pilot.json` |
| `apps/openclaw/scripts/install_gateway_24_7.sh` | OpenClaw gateway LaunchAgent |
| `apps/openclaw/scripts/install_daily_launchd.sh` | Daily pilot LaunchAgent (no LLM) |
| `apps/openclaw/scripts/setup_whatsapp.sh` | WhatsApp channel setup |
| `openclaw gateway` / `openclaw dashboard` | OpenClaw CLI (external) |

Env overrides: `SIGNAL_DATE`, `SECTOR_JOBS`, `WORKERS`, `PERIOD_WORKERS`, `EXPORT_BUY`, `SEND_TELEGRAM`

---

## Production backtests (direct)

Usually invoked via `pipelines` or `run_trading.py backtest --engine <alias>`; call directly when debugging.

| Script | Engine alias | Purpose |
|--------|--------------|---------|
| `scripts/backtests/run_halal_sector_month_pilot.py` | `halal-sector-pilot` | Sector/month Phoenix+FA pilot → `master_pilot.json` |
| `scripts/backtests/run_halal_orchestrator_backtest_2025.py` | `halal-orchestrator-2025` | Large halal TA+FA backtest |
| `scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py` | `phoenix-fund-2025` | Phoenix+FA fusion backtest |
| `scripts/backtests/run_phoenix_orchestrator_backtest_2025.py` | `phoenix-orchestrator-2025` | Phoenix orchestrator backtest |
| `scripts/backtests/run_orchestrator_backtest.py` | `orchestrator-legacy` | Legacy orchestrator backtest |
| `scripts/backtests/run_sector_backtest.py` | `sector-legacy` | Legacy sector backtest |

---

## Dashboard & exports

| Command | Purpose |
|---------|---------|
| `./bin/mts dashboard` | Start dashboard on http://localhost:3055 |
| `./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD` | Reconcile BUY+WATCH → Excel + JSON |
| `scripts/run_phoenix_sector_scan.py` | Run Phoenix sector scan |
| `scripts/dashboard/export_phoenix_buy_from_masters.py` | Delegates to `core.io.export` |

---

## Predictions (archived)

These scripts have been moved to `archive/scripts/prediction-legacy/`:

| Archived script | Purpose |
|-----------------|---------|
| `run_halal_predictions.py` | Halal universe prediction batch |
| `run_live_predictions.py` | Live prediction run |
| `run_pure_prediction.py` | Pure prediction mode (no forward labels) |
| `run_backtest_excel.py` | Excel backtest with outcome labels |
| `run_yearly_backtest.py` | Multi-period driver |
| `run_multi_timeframe_backtest.py` | Multiple cutoff dates |

Shared constants: `core/universe/` (sectors, halal lists); `backtests/common.py` is a re-export shim.

---

## Archived scripts

All of these have been moved to `archive/scripts/`:

| Archive folder | Contents |
|----------------|----------|
| `prediction-legacy/` | `run_halal_predictions.py`, `run_backtest_excel.py`, `run_pure_prediction.py`, etc. |
| `analysis/` | Score analysis, regression tests, threshold tuning |
| `polygon/` | Polygon data client, trade scanner, KGC explorer |
| `data-prep/` | `extract_halal_universe.py`, `_classify_master.py`, etc. |
| `backtests-legacy/` | `run_master_data_parallel_pilot.py`, `run_halal_technical_backtest_2025.py`, etc. |
| `legacy-dashboard/` | Old dashboard generators |

---

## Shims & agent CLIs

| Command | Purpose |
|---------|---------|
| `scripts/run_orchestrator_tickers.py` | Thin shim → `run_trading.py analyze` (defaults `ta-fa`) |
| `fundamental-agent` | `agents/fundamental/cli.py` (setuptools entry) |
| `technical-agent` | `agents/technical/cli.py` |
| `oneil-agent` | `agents/oneil/cli.py` |

---

## Library (not run directly)

| Path | Purpose |
|------|---------|
| `scripts/lib/run_bundle.py` | `run_bundle.json` aggregation |
| `pipelines/*.py` | Pipeline implementations |
| `core/` | Shared paths, contracts, I/O |

---

## Archived scripts

Retired one-offs live under **`archive/`** (legacy backtests, dev tests, old dashboard converters). See `archive/README.md`. Not for production use.

---

## Quick recipes

```bash
# Dashboard
./bin/mts dashboard

# All-sector backtest (default date = yesterday)
./bin/mts unified --date 2026-05-28

# Sector + dashboard together
./bin/mts lab sector --sector Energy --date 2026-05-28

# Single ticker
./bin/mts analyze --ticker AAPL --date 2026-05-28

./bin/mts export --from 2026-05-10 --to 2026-05-28   # BUY+WATCH Excel + JSON
./bin/mts dashboard && open http://localhost:3055/research/signals

**Do not** use `agents/orchestrator/service.py` for Phoenix workflows — that path is TA+FA LangGraph only.

See also: [MODULE_MAP.md](../MODULE_MAP.md), [STRUCTURE.md](../STRUCTURE.md), [docs/BACKTEST_PLAYBOOK.md](./BACKTEST_PLAYBOOK.md)
