---
name: sector-pilot
description: Run a single-sector halal master_pilot backtest (e.g. Energy) for a signal date and report BUY/WATCH summary.
metadata:
  openclaw:
    requires:
      bins: ["bash"]
---

# Sector pilot (single sector)

Use when the user asks for a **sector backtest** (e.g. "energy 15-05-2026", "run Energy pilot for 2026-05-15").

## Command

Replace `ABS_PATH` with repo root (`repoRoot` / Runtime). Parse sector name and `YYYY-MM-DD` from the user message.

```bash
cd ABS_PATH && ABS_PATH/bin/mts sector --sector "Energy" --date 2026-05-15
```

Or with dashboard: `ABS_PATH/bin/mts lab sector --sector "Energy" --date 2026-05-15`

Common sectors: Energy, Technology, Healthcare, Financials, Industrials, Consumer Staples, etc. (must match `halal_tickers_clean.json`).

Optional env: `WORKERS=8`, `PERIOD_WORKERS=2`.

## After run

- Output: `data/output/trading_runs/sector_<slug>_<date>/master_pilot.json`
- Logs: terminal output from pipeline (also in OpenClaw exec log)

Summarize: ticker count, Phoenix BUY list, WATCH count, confusion overall if present, errors.

## Do not

- Re-implement backtest logic in the model; always run `bin/mts sector` or `bin/mts unified`.
