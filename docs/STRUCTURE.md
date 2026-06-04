# Project Structure

```
MyTradingSpace/
├── bin/
│   └── mts                  # Control plane CLI
├── cli/
│   └── __main__.py          # CLI implementation
├── pipelines/
│   ├── analyze.py           # Single-ticker analyze
│   ├── sector.py            # Single-sector pilot
│   ├── unified.py           # All-sector unified pilot
│   └── daily.py             # Daily pipeline
├── agents/
│   ├── phoenix/             # Phoenix pattern/stage scoring (production TA)
│   ├── fundamental/         # Fundamental analysis
│   ├── orchestrator/        # Phoenix+FA fusion (CWAF)
│   └── polygon_data/        # Shared Polygon client
├── core/
│   ├── universe/            # HALAL_SECTORS, MONTHS, confusion helpers
│   ├── data/polygon.py      # Polygon client re-export
│   ├── io/                  # export.py, master_pilot.py
│   ├── contracts/           # fusion.py, envelope.py
│   └── paths.py             # Path constants
├── apps/
│   ├── backtest-dashboard/  # Next.js Research Lab
│   └── openclaw/            # WhatsApp automation
├── data/
│   ├── input/master_data/   # Halal universe, sector tickers
│   ├── output/trading_runs/ # Production outputs (gitignored)
│   └── archive/             # Archived runs
├── docs/                    # All documentation
│   ├── specs/               # Agent specs, ADRs
│   ├── plans/               # PRODUCTION_PLAN, REFACTOR_PLAN
│   ├── agent-learning/      # Steering guides
│   ├── strategies/          # Trading strategies
│   └── prompts/             # Agent prompts
├── backtests/common.py      # Shim → core/universe
└── archive/                 # Retired scripts & tests
```

## Entry Points

| Task | Command |
|------|---------|
| Dashboard | `./bin/mts dashboard` |
| Single-ticker | `./bin/mts analyze --ticker AAPL` |
| Sector pilot | `./bin/mts sector --sector Energy` |
| Unified pilot | `./bin/mts unified` |
| Daily pipeline | `./bin/mts daily` |
| Export signals | `./bin/mts export` |

## Agent Architecture

```
bin/mts → cli/__main__.py → pipelines/* → agents/*
                                        → core/io/*
```

## Data Flow

```
Polygon/FMP APIs → agents/* → pipelines/* → data/output/trading_runs/
                                          → apps/backtest-dashboard/
```
