# Backtest registry (local persistence)

Labeled backtest runs are indexed in a **local SQLite database** so the Research Lab dashboard can show per-agent confusion heatmaps immediately after each run.

## Default location

```
data/output/backtest_registry/backtests.sqlite
```

Tables:

| Table | Purpose |
|-------|---------|
| `backtest_runs` | One row per artifact (`master_pilot.json` or `confusion_matrix.json`) |
| `agent_matrices` | TP/FP/TN/FN + accuracy per agent (`by_agent`) |
| `backtest_tickers` | Per-ticker summary rows for drill-down |

JSON artifacts under `data/output/trading_runs/` remain the **source of truth**. SQLite is an index for fast dashboard queries and historical timeline views.

## Sync commands

```bash
# Scan all trading_runs artifacts and upsert registry
./bin/mts backtest sync

# Daily pipeline auto-ingests unified master_pilot after pilot completes
./bin/mts daily --date YYYY-MM-DD
```

Sector / ticker pilots also ingest at the end of:

- `scripts/backtests/run_halal_sector_month_pilot.py`
- `scripts/backtests/run_master_data_parallel_pilot.py`

## Dashboard (canonical UI)

All labeled backtest results are indexed for the **Backtest registry** page — this is the primary place to review TP/FP/TN/FN, agent heatmaps, and FN diagnostics.

```
http://localhost:3055/research/backtests
```

Deep-link one run (printed at end of every pilot):

```
http://localhost:3055/research/backtests?run=data/output/trading_runs/sector_.../master_pilot.json
```

The page auto-syncs on load. Command Center jobs (sector/unified/daily) also sync the registry when they finish successfully.

Launch runs from **Research Lab → Command Center** (`/research/console`); use the **View run in Backtest registry** link on completed jobs.

## Intelligence agents + PIT gating

Historical evaluation of macro/news/insider/sentiment/geopolitics uses point-in-time rules in `core/evaluation/pit_policy.py`. Enable during a labeled pilot:

```bash
python scripts/backtests/run_halal_sector_month_pilot.py \
  --tickers AAPL --signal-date 2025-06-01 \
  --intelligence-agents
```

Requirements for deep history:

| Agent | Keys / config |
|-------|----------------|
| Macro | `FRED_API_KEY` |
| Market summary | `POLYGON_API_KEY` |
| News (history) | `FINNHUB_API_KEY`, `NEWS_DATA_SOURCE=finnhub` |
| Insider (history) | `SEC_EDGAR_USER_AGENT`, `INSIDER_DATA_SOURCE=edgar` |

## Persistence options (local)

| Option | Pros | Cons |
|--------|------|------|
| **SQLite (default)** | Fast queries, single file, works offline | Not shared across machines |
| **JSON artifacts only** | Human-readable, git-friendly snapshots | Slow to aggregate many runs |
| **Google Drive / One backup** | Off-machine backup of `backtest_registry/` + `trading_runs/` | Not a live DB; sync manually or via rclone |
| **DuckDB file** | Good for analytics at scale | Extra dependency; not wired yet |

**Recommendation:** keep SQLite + periodic backup of `data/output/backtest_registry/` and `data/output/trading_runs/` to Google Drive (or Time Machine). The dashboard reads SQLite; artifacts remain recoverable if the DB is rebuilt via `./bin/mts backtest sync`.

## Rebuild registry from artifacts

If the SQLite file is lost or corrupted:

```bash
rm -f data/output/backtest_registry/backtests.sqlite
./bin/mts backtest sync
```

All indexed runs are reconstructed from existing `master_pilot.json` / `confusion_matrix.json` files.
