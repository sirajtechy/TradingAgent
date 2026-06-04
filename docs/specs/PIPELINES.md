# Pipeline contracts (spec-driven)

Pipelines are **agent-agnostic orchestrators**. They accept structured inputs and delegate to existing scripts or `pipelines.analyze` — no scoring logic inside pipeline modules.

## Entry point

```bash
python -m pipelines <command> [options]
```

| Command | Module | Delegates to |
|---------|--------|--------------|
| `analyze` | `pipelines/analyze.py` | Phoenix / FA / orchestrator services |
| `sector` | `pipelines/backtest.py` | `scripts/backtests/run_halal_sector_month_pilot.py` |
| `unified` | `pipelines/backtest.py` | `scripts/backtests/run_master_data_parallel_pilot.py` |
| `daily` | `pipelines/daily.py` | unified + BUY excel + notify |

## Outputs (unchanged)

| Pipeline | Artifact path |
|----------|---------------|
| sector | `data/output/trading_runs/sector_<slug>_<date>/master_pilot.json` |
| unified | `data/output/trading_runs/unified_master_<date>/master_pilot.json` |
| daily | above + `phoenix_buy_<date>.xlsx` |

## OpenClaw mapping

| Skill | Pipeline / script |
|-------|-------------------|
| trading-orchestrator | `openclaw/scripts/orchestrator_analyze.sh` → `pipelines.analyze` |
| daily-unified-pilot | `run_daily_pipeline.sh` → `python -m pipelines daily` |
| sector-pilot | `python -m pipelines sector` |
| phoenix-only / fundamental-only | `--fusion phoenix` / `--fusion fundamental` |

## Core I/O

Shared merge/confusion: `core/io/master_pilot.py` (`confusion_from_master_tickers`, `slug_sector`).

Paths: `core/paths.py` (extends repo `paths.py`).

See also: [ADR-001-agent-envelope.md](./ADR-001-agent-envelope.md)
