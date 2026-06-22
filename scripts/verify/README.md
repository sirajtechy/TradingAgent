# Backtest output verification (audit-only)

Standalone utility that **re-fetches Polygon market data** and checks whether
price and outcome fields in finished backtest artifacts match independent
recomputation.

## Important

- **Do not** wire this into `run_halal_sector_month_pilot.py`, pipelines, or the dashboard.
- **Do not** run during active backtests if you want to conserve Polygon quota.
- Run **after** a backtest completes on a stable `master_pilot.json` (or related artifact).

## What it verifies

| Field | Check |
|-------|--------|
| `entry_price` / `start_price` | Polygon adjusted close on or before `signal_date` |
| `exit_reference_price` | Polygon close on or before `result_date` |
| `target_hit` | Any daily High ≥ `target_price` in eval window |
| `target_hit_date` | First bar date crossing target |
| `signal_correct*` | Derived from signal direction + recomputed target hit |

It does **not** re-run Phoenix, fusion, or pattern detection.

## Usage

```bash
cd MyTradingSpace
set -a && source .env && set +a

# Single completed run
python scripts/verify/verify_backtest.py \
  --input data/output/trading_runs/sector_information-technology_2025-04-02/master_pilot.json \
  --rate-limit 2

# All runs under a directory (one master_pilot.json per subfolder)
python scripts/verify/verify_backtest.py \
  --input data/output/trading_runs \
  --rate-limit 2

# Spot-check 20 random rows
python scripts/verify/verify_backtest.py \
  --input path/to/master_pilot.json \
  --sample 20

# Parse-only (no Polygon calls)
python scripts/verify/verify_backtest.py --input path/to/master_pilot.json --dry-run
```

Reports are written to `data/output/verify/<run>_verify_report.json`.

Exit codes: `0` = all checked rows pass, `2` = one or more failures, `1` = usage/input error.

## Supported inputs

- `master_pilot.json` (preferred)
- `pilot_results.json` (richest period-level detail)
- `run_bundle.json`

When multiple formats exist in one folder, `master_pilot.json` is preferred.

## Tests

```bash
pytest tests/test_verify_backtest.py -q
```

No live Polygon API calls in unit tests.
