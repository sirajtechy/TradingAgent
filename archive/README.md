# Archive

Historical scripts and backtest drivers kept for reference. **Not used in production.**

Production paths:

- Control plane: `./bin/mts` (dashboard, analyze, sector, unified, lab, export, daily)
- Analyze: `./bin/mts analyze --ticker AAPL --date YYYY-MM-DD`
- Unified pilot: `./bin/mts unified --date YYYY-MM-DD`
- OpenClaw: `apps/openclaw/scripts/orchestrator_analyze.sh`

## Contents

| Path | What |
|------|------|
| `agents/` | Retired agent packages: `technical/`, `oneil/`, `prediction/`, `orchestrator-ta-fa/` (TA+FA LangGraph path) |
| `backtests/` | Legacy sector-scale drivers (`run_fundamental.py`, `run_technical.py`, …) superseded by `scripts/backtests/` engines |
| `scripts/backtests-smoke/` | Single-ticker / audit runners not registered in `BACKTEST_ENGINES` |
| `scripts/dev-tests/` | Ad-hoc ticker date experiments |
| `scripts/legacy-dashboard/` | Static JSON → dashboard converters superseded by live `/api/trading-runs` |
| `scripts/workstreams/` | One-off RCA / workstream experiments |

Shared universe constants remain in `backtests/common.py` (imported by `run_trading.py`).
