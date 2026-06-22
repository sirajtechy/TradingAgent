# Backtest Dashboard (Research Lab)

Next.js **App Router** UI for MyTradingSpace daily workflow and deep research.

**Default entry:** `/` redirects to **`/research`** (Overview).

## Active routes

| Path | Purpose |
| --- | --- |
| `/research` | **Overview** — agent data sources, BUY/WATCH pre-trade table (entry/stop/targets + analyze status) |
| `/research/phoenix` | Phoenix pilot — full `master_pilot.json` table, Excel export |
| `/research/analyze` | Single-ticker deep analyze (8 agents + SEC insider) |
| `/research/analyze/watchlist` | BUY/WATCH batch deep dive |
| `/research/signals` | Reconciled export (`phoenix_signals_reconciled.json`) |
| `/research/portfolio` | Momentum allocation book |
| `/research/runs` | Browse/compare trading run bundles |

Legacy redirects: `/phoenix-watch-buy` → phoenix, `/trading-runs` → runs, `/sectors` & `/halal` → overview.

## API (filesystem-backed)

| API | Data |
| --- | --- |
| `/api/research/overview` | Master pilot + watchlist analyze status + agent source matrix |
| `/api/trading-runs`, `/bundle`, `/compare` | `data/output/trading_runs/` |
| `/api/research/signals` | `phoenix_signals_reconciled.json` |
| `/api/analyze`, `/watchlist` | `data/output/research/<date>/` + pipeline spawn |
| `/api/portfolio`, `/allocation` | Portfolio outputs |

## Legacy (archived)

Pre–Research Lab CWAF dashboard parked under **`archive/legacy-dashboard/`** (static JSON, not `./bin/mts daily`).

## Commands

```bash
npm install
npm run dev       # http://localhost:3000
npm run build
npm run start     # production; PORT=3055 via ./bin/mts dashboard -b
```

Parent: **`../README.md`**, **`../Trading-Journals/DailyCommands.md`**.
