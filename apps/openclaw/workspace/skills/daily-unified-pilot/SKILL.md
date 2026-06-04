---
name: daily-unified-pilot
description: Run today's all-sector unified master_pilot backtest (537 tickers) and report BUY/WATCH summary.
metadata:
  openclaw:
    requires:
      bins: ["bash"]
---

# Daily unified sector pilot

Use when the user asks to **run today's backtest**, **run all sectors**, **build master_pilot**, or **pre-market pilot**.

## Command

Replace `ABS_PATH` with repo root (`repoRoot` / Runtime).

```bash
ABS_PATH/bin/mts daily --date YYYY-MM-DD
```

Or full pipeline with legacy shell: `ABS_PATH/openclaw/scripts/run_daily_pipeline.sh`

Optional: `EXPORT_BUY=0`, `SEND_TELEGRAM=0` via `bin/mts daily --no-export-buy --no-telegram`.

## After run

- Merged JSON: `data/output/trading_runs/unified_master_<date>/master_pilot.json`
- BUY excel (if enabled): `data/output/trading_runs/phoenix_buy_<date>.xlsx`
- Logs: `data/output/trading_runs/logs/daily_pipeline_<date>.log`

Summarize: ticker count, Phoenix BUY list, confusion overall if present, errors.

## Do not

- Re-implement backtest logic in the model; always run the script.
