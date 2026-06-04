# Backtest Dashboard

Next.js (**App Router**) UI for exploring halal predictions, sector views, Phoenix scans, and **`run_bundle` / `master_pilot`** outputs produced under `../data/output/`.

## App structure

| Path | Role |
| --- | --- |
| `app/page.tsx` | Dashboard home / links |
| `app/halal/`, `app/sectors/` | Halal and sector pages |
| `app/phoenix-scans/` | Phoenix scan browser |
| `app/trading-runs/` | Trading run bundles + compare (reads `data/output/trading_runs/`) |
| `app/phoenix-watch-buy/` | Sector master pilot table (TP/FP/TN/FN, sort, Excel export) |
| `app/lib/` | Shared TS helpers (`confusionBucket`, `compareRunBundles`, …) |
| `app/api/trading-runs/` | `route.ts`, `bundle/`, `compare/` — filesystem-backed JSON for local QA |
| `app/api/phoenix-scans/`, `halal-predictions/`, `sectors-predictions/` | Other JSON-backed endpoints |

Static or generated JSON samples may live under `app/data/` where noted in code.

## Commands

```bash
npm install
npm run dev       # http://localhost:3000
npm run build
npm run start     # production; set PORT if needed (e.g. PORT=3055)
npm run lint
```

The dashboard expects the Python repo’s **`data/output/`** tree to exist relative to the monorepo root (paths are resolved from the Next server process cwd / repo layout — run from `MyTradingSpace` context as in your usual workflow).

## Parent project

See **`../README.md`** and **`../MODULE_MAP.md`** for the full multi-agent layout and canonical `scripts/run_trading.py` CLI.
