# Configuration Reference

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLYGON_API_KEY` | Yes | - | Polygon.io API key for market data |
| `FMP_API_KEY` | Yes | - | Financial Modeling Prep API key |
| `MYTRADING_PYTHON` | No | `.venv/bin/python` | Python interpreter path |
| `POLYGON_REQUESTS_PER_SECOND` | No | `5` | Rate limit for Polygon API |
| `SEND_TELEGRAM` | No | `0` | Enable Telegram notifications in daily pipeline |
| `TELEGRAM_BOT_TOKEN` | No | - | Telegram bot token (if SEND_TELEGRAM=1) |
| `TELEGRAM_CHAT_ID` | No | - | Telegram chat ID (if SEND_TELEGRAM=1) |

## CLI Commands

### `./bin/mts dashboard`

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `3055` | Dashboard port |
| `--background` | `false` | Run in background |

### `./bin/mts analyze`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--ticker` | Yes | - | Stock ticker symbol |
| `--date` | No | Yesterday | Signal date (YYYY-MM-DD) |
| `--fusion` | No | `phoenix-fa` | Fusion mode: `phoenix-fa`, `phoenix`, `fundamental`, `ta-fa` |
| `--fund-data-source` | No | `yfinance` | Data source: `yfinance`, `fmp` |

### `./bin/mts sector`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--sector` | Yes | - | Sector name (e.g., "Energy") |
| `--date` | No | Yesterday | Signal date |
| `--eval-days` | No | `15` | Evaluation window in days |

### `./bin/mts unified`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--date` | No | Yesterday | Signal date |
| `--eval-days` | No | `15` | Evaluation window in days |

### `./bin/mts daily`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--no-export-buy` | No | `false` | Skip BUY export step |

### `./bin/mts export`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--from` | No | 14 days ago | Start date |
| `--to` | No | Yesterday | End date |
| `--signals` | No | `BUY,WATCH` | Signal types to include |
| `--lookback-days` | No | `14` | Default lookback if --from omitted |
| `--no-archive` | No | `false` | Skip archived runs |
| `--json-only` | No | `false` | Output JSON only (no Excel) |

### `./bin/mts lab`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--date` | No | Yesterday | Signal date |
| `--port` | No | `3055` | Dashboard port |

Subcommands: `sector`, `unified`

## Fusion Modes

| Mode | Agents Used | Weights | Description |
|------|-------------|---------|-------------|
| `phoenix-fa` | Phoenix + Fundamental | 90% / 10% | Default. Phoenix pattern + FA health check |
| `phoenix` | Phoenix only | 100% Phoenix | Pure technical pattern analysis |
| `fundamental` | Fundamental only | 100% Fund | Financial health and valuation only |
| `ta-fa` | Technical + Fundamental | CWAF | Legacy TA agent + Fundamental fusion |

## Agent Registry

Located in `agents/_registry.py`:

```python
AGENT_REGISTRY = {
    "phoenix": AgentSpec(...),
    "fundamental": AgentSpec(...),
    "technical": AgentSpec(...),
    "orchestrator-ta-fa": AgentSpec(...),
}
```

## Halal Universe

Located in `core/universe/`:

```python
HALAL_SECTORS = {
    "Technology": ["AAPL", "MSFT", ...],
    "Healthcare": ["JNJ", "UNH", ...],
    "Energy": ["XOM", "CVX", ...],
    # ... 12 sectors total
}
```

## Output Paths

| Path | Description |
|------|-------------|
| `data/output/trading_runs/` | Active trading run outputs |
| `data/output/trading_runs/<run_id>/master_pilot.json` | Per-run pilot results |
| `data/output/trading_runs/phoenix_signals_reconciled.xlsx` | Exported signals |
| `data/output/trading_runs/phoenix_signals_reconciled.json` | Signals for dashboard |
| `data/archive/trading_runs/` | Archived runs |
| `data/output/.mts/` | PID files for background processes |

## Dashboard Routes

| Route | API Endpoint | Data Source |
|-------|--------------|-------------|
| `/research/signals` | `/api/research/signals` | `phoenix_signals_reconciled.json` |
| `/research/phoenix` | `/api/trading-runs/bundle` | `master_pilot.json` |
| `/research/runs` | `/api/trading-runs` | `data/output/trading_runs/` |
| `/research/scans` | `/api/phoenix-scans` | Scan JSON files |

## Phoenix Scoring

| Component | Weight | Description |
|-----------|--------|-------------|
| Stage score | 30% | Market stage (1-6) |
| Pattern score | 40% | Chart patterns detected |
| Risk score | 30% | Entry/stop/target quality |

## Signal Thresholds

| Signal | Score Range | Description |
|--------|-------------|-------------|
| BUY | ≥ 70 | Strong buy signal |
| WATCH | 50-69 | Monitor for entry |
| AVOID | < 50 | Do not trade |

## Rate Limiting

Polygon API rate limiting is handled by `agents/polygon_data/`:

```python
_RATE_LIMIT_RPS = float(os.environ.get("POLYGON_REQUESTS_PER_SECOND", "5"))
```

Token bucket algorithm with exponential backoff on 429 responses.
