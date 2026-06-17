# MyTradingSpace — Multi-Agent Stock Analysis Platform

A **deterministic, rule-based** halal-universe screening stack: **Phoenix** (pattern/stage TA) + **Fundamental** analysis fused via orchestrator **CWAF** (default **90% Phoenix / 10% FA**). Outputs feed `master_pilot.json` backtests and the **Research Lab** dashboard at http://localhost:3055.

**Extended intelligence (opt-in):** eight agents (macro, market, news, **SEC EDGAR insider**, sentiment, geopolitics) + four trader strategy profiles + a momentum **portfolio engine**.

**Control plane:** `./bin/mts` — one entry for dashboard, backtests, analyze, export, portfolio, and daily ops.

**Operator journals:** [Trading-Journals/](./Trading-Journals/) — daily commands cheat sheet + full project journal.

**Changelog:** [docs/CHANGELOG.md](./docs/CHANGELOG.md)

---

## Quick Start

```bash
cd MyTradingSpace
cp .env.example .env          # see Environment section below
python3 -m pip install -e .
cd apps/backtest-dashboard && npm install && cd ../..

set -a && source .env && set +a
./bin/mts config validate     # optional: validate .env keys

# Demo: backtest all sectors + dashboard
./bin/mts lab unified

# Open Research Lab
#   http://localhost:3055/research/phoenix      — BUY/WATCH board
#   http://localhost:3055/research/analyze      — single-ticker deep dive
#   http://localhost:3055/research/analyze/watchlist — BUY/WATCH batch deep dive
#   http://localhost:3055/research/portfolio    — momentum allocation book
```

---

## Daily workflow (production)

See **[Trading-Journals/DailyCommands.md](./Trading-Journals/DailyCommands.md)** for the full ship-it list.

```bash
set -a && source .env && set +a

./bin/mts daily                 # unified backtest + BUY excel + notify
./bin/mts export                # reconciled BUY/WATCH → Excel + JSON
./bin/mts dashboard -b          # Research Lab (background)
./bin/mts stop                  # when done
```

**Deep research on a name or watchlist (after daily):**

```bash
./bin/mts analyze --ticker AAPL --fusion full --export-breakdown --refresh-context
./bin/mts analyze --watchlist --fusion full --export-breakdown --refresh-context
```

---

## Research Lab dashboard

Next.js app: `apps/backtest-dashboard/` · default port **3055**

| Route | Purpose |
|-------|---------|
| `/research` | Research Lab hub |
| `/research/phoenix` | `master_pilot.json` — BUY/WATCH, TP/FP, **Already up**, Trade focus |
| `/research/analyze` | **Deep analyze** — single ticker, all agents, fusion score, per-agent panels |
| `/research/analyze/watchlist` | **BUY/WATCH batch** — deep dive every name in today's `master_pilot.json` |
| `/research/portfolio` | Momentum allocation book + backtest KPIs |
| `/research/runs` | Browse all backtest run bundles |
| `/research/signals` | Reconciled BUY/WATCH export |
| `/research/scans` | Phoenix sector scans |

### Deep Analyze UI

Select a ticker (or open from watchlist). The layout shows:

- **Fusion hero** — orchestrator score, final signal, advisory verdict
- **Agent sidebar** — Phoenix, Fundamental, Macro, Market Summary, Geopolitics, News, **Insider**, Sentiment
- **Per-agent detail** — one-liner, bullets, metrics, headlines (news), **insider sale table**, source tier badges

Cached JSON lives at `data/output/research/<date>/<TICKER>_analyze.json`. Re-run with `--refresh-context` after API key changes.

---

## Commands (`bin/mts`)

### Core production

| Command | Purpose |
|---------|---------|
| `./bin/mts dashboard` | Start dashboard (dev mode, foreground) |
| `./bin/mts dashboard -b` | Start dashboard in background (production build) |
| `./bin/mts stop` | Stop background dashboard on port 3055 |
| `./bin/mts sector --sector "Information Technology" --date YYYY-MM-DD` | Single-sector pilot (~50 tickers) |
| `./bin/mts unified --date YYYY-MM-DD` | All-sector unified pilot |
| `./bin/mts lab unified --date YYYY-MM-DD` | Unified backtest + start dashboard |
| `./bin/mts daily` | Daily pipeline (unified + BUY excel + notify) |
| `./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD` | Reconcile BUY/WATCH signals |

### Analyze & intelligence

| Command | Purpose |
|---------|---------|
| `./bin/mts analyze --ticker AAPL --date YYYY-MM-DD` | Single-ticker JSON (`--fusion phoenix-fa\|phoenix\|fundamental\|full`) |
| `./bin/mts analyze --ticker AAPL --fusion full --export-breakdown` | All 8 agents + markdown breakdown |
| `./bin/mts analyze --ticker AAPL --fusion full --refresh-context` | Bypass stale `context_<date>.json` cache |
| `./bin/mts analyze --watchlist --fusion full --export-breakdown` | Batch analyze all BUY/WATCH tickers |
| `./bin/mts analyze --watchlist --max-tickers 5 --force` | Cap batch size; re-run cached tickers |
| `./bin/mts agent insider --ticker AAPL --date YYYY-MM-DD` | Standalone insider agent JSON |
| `./bin/mts agent macro --date YYYY-MM-DD` | Session macro (no ticker) |
| `./bin/mts context --date YYYY-MM-DD` | Macro + market_summary + geopolitics → one JSON file |
| `./bin/mts strategy --ticker AAPL --profile blend` | Minervini / Moglen / Breitstein / McIntosh layers |

### Portfolio intelligence

| Command | Purpose |
|---------|---------|
| `./bin/mts portfolio backtest --start 2024-01-01 --end 2025-12-31` | Momentum book simulation |
| `./bin/mts portfolio allocate --budget 200000 --date YYYY-MM-DD` | Advisory 20-name book |
| `./bin/mts portfolio allocate --full-agents --enrich-max 10` | Top names get full agent enrich |

Spec: [docs/specs/PORTFOLIO_ENGINE.md](./docs/specs/PORTFOLIO_ENGINE.md)

### Loop engineering (feature automation)

| Command | Purpose |
|---------|---------|
| `./bin/mts loop triage` | Rank `.loop/roadmap.yaml` backlog |
| `./bin/mts loop ops --date YYYY-MM-DD` | Read-only daily ops health check |

See [AGENTS.md](./AGENTS.md) and `.loop/policies/`.

**Defaults**

- `--date` = yesterday (today for `daily`); override globally: `./bin/mts --date 2026-06-03 unified`
- `--eval-days` = **15** calendar days for forward target-hit labeling (TP/FP)

**Halal sector names** (exact strings for `--sector`): Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities.

---

## Agents

### Production (daily backtest)

| Agent | Role | Primary data |
|-------|------|--------------|
| **Phoenix** | Pattern/stage scoring, entry/stop/targets, extension guardrail | Polygon OHLCV |
| **Fundamental** | Financial + shariah scoring | FMP / yfinance |
| **Orchestrator** | Phoenix+FA CWAF fusion (`phoenix-fa`) | — |

### Intelligence (full fusion / `--fusion full`)

| Agent | Role | Primary data | Fallback |
|-------|------|--------------|----------|
| **Macro** | Fed funds, CPI, unemployment, yield curve | **FRED** (`FRED_API_KEY`) | yfinance ^TNX/^IRX |
| **Market summary** | VIX, SPY 20d, sector leaders/laggards | Polygon + FRED | yfinance VIX (Polygon `I:VIX` 403 on free tier) |
| **News** | Headlines + analyst grades | FMP → **Finnhub** | yfinance news |
| **Insider** | Form 4 common-stock **code S** sales | **SEC EDGAR** | FMP → yfinance |
| **Geopolitics** | Geo keyword scan on headlines | FMP general news | yfinance ETF/news scan |
| **Sentiment** | Composite of upstream agents | Derived (no own API) | — |

### Trader strategies (`--strategy-profile`)

| Profile | Module |
|---------|--------|
| `minervini` | VCP, trend template, chase guard |
| `moglen` | RMV, regime guard, setup pack |
| `breitstein` | VWAP context, trend character |
| `mcintosh` | Leader rank, position tiers |
| `blend` | Meta-signal across all four |

Legacy agents live under **`archive/agents/`** — not used in daily production.

---

## SEC EDGAR insider agent (new)

Authoritative insider **sales** from SEC Form 4 filings — free, no paid API required.

**Pipeline:** `Ticker → CIK → recent Form 4s → parse XML → sum code "S" rows`

| Rule | Detail |
|------|--------|
| Transaction filter | `nonDerivativeTransaction` only |
| Code | `transactionCode == "S"` (open-market sale) |
| Security | `securityTitle` contains **Common Stock** (excludes RSU/option rows) |
| Value | `shares × price`; skip rows with missing/zero price |
| Dedup | Original + amended Form 4 filings deduplicated |

**Dashboard output (Insider panel):**

- Totals: dollar sold, shares sold, average sale price
- **Who sold** table: insider name, **when** (date or range), sale count, shares, avg price, total $
- Recent individual sales with transaction dates

**CLI example:**

```bash
export SEC_EDGAR_USER_AGENT="Your Name you@email.com"   # required by SEC
./bin/mts agent insider --ticker CRWV --date 2026-06-13
./bin/mts analyze --ticker CRWV --fusion full --export-breakdown --refresh-context
```

Config: `INSIDER_DATA_SOURCE=auto|edgar|fmp|yfinance` (default `auto` prefers EDGAR).

Implementation: `agents/insider/edgar_client.py` · Tests: `tests/test_insider_edgar.py`

---

## Environment

Copy `.env.example` → `.env`. Never commit `.env`.

```bash
python3 -m pip install -e ".[dev]"
cd apps/backtest-dashboard && npm install
```

### Required / recommended keys

| Variable | Used by | Notes |
|----------|---------|-------|
| `POLYGON_API_KEY` | Phoenix, FA, market summary | Required for production backtests |
| `FRED_API_KEY` | Macro, market summary | Free at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `SEC_EDGAR_USER_AGENT` | Insider (EDGAR) | **Required for SEC** — `"Name email@domain.com"` |
| `FMP_API_KEY` | News grades, geopolitics, FA | Optional; many endpoints need paid tier (402) |
| `FINNHUB_API_KEY` | News | Optional free tier before yfinance fallback |

### Data source overrides

| Variable | Values | Default |
|----------|--------|---------|
| `MACRO_DATA_SOURCE` | `auto\|fred\|yfinance` | `auto` |
| `NEWS_DATA_SOURCE` | `auto\|fmp\|yfinance` | `auto` |
| `INSIDER_DATA_SOURCE` | `auto\|edgar\|fmp\|yfinance` | `auto` (EDGAR first) |
| `GEOPOLITICS_DATA_SOURCE` | `auto\|fmp\|yfinance` | `auto` |
| `MARKET_DATA_SOURCE` | `auto\|polygon\|yfinance` | `auto` |

Validate: `./bin/mts config validate`

After changing keys, refresh cached session context:

```bash
./bin/mts analyze --ticker AAPL --fusion full --refresh-context
```

Full data plan: [docs/specs/INTELLIGENCE_DATA_PLAN.md](./docs/specs/INTELLIGENCE_DATA_PLAN.md) · Free sources: [docs/specs/FREE_DATA_SOURCES.md](./docs/specs/FREE_DATA_SOURCES.md)

---

## Project structure

```
MyTradingSpace/
├── bin/mts                  # Control plane CLI
├── cli/                     # CLI implementation
├── pipelines/               # analyze, sector, unified, daily, watchlist, backtest
├── agents/
│   ├── phoenix/             # Pattern/stage + extension guardrail
│   ├── fundamental/
│   ├── orchestrator/        # Fusion, agent_breakdown, pipeline_full
│   ├── macro/               # FRED + yfinance fallback
│   ├── market_summary/
│   ├── news/                # FMP, Finnhub, yfinance
│   ├── insider/             # SEC EDGAR edgar_client.py + rules
│   ├── sentiment/
│   ├── geopolitics/
│   ├── portfolio/           # Momentum rank, FRR, simulator, enrich
│   ├── strategies/          # Minervini, Moglen, Breitstein, McIntosh
│   └── polygon_data/
├── core/                    # universe, export, contracts, config_schema, paths
├── apps/
│   ├── backtest-dashboard/  # Research Lab UI (+ /research/analyze)
│   └── openclaw/
├── Trading-Journals/
├── .loop/                   # Loop engineering control plane
├── docs/                    # Specs, CHANGELOG, architecture
├── data/
│   ├── input/               # Halal universe
│   ├── config/              # portfolio_rules.json
│   └── output/              # trading_runs, research, context (gitignored)
└── archive/
```

---

## Output locations

| Path | Contents |
|------|----------|
| `data/output/trading_runs/unified_master_<date>/master_pilot.json` | All-sector backtest |
| `data/output/trading_runs/sector_<slug>_<date>/master_pilot.json` | Single-sector backtest |
| `data/output/trading_runs/phoenix_signals_reconciled.xlsx` | Export BUY/WATCH |
| `data/output/research/<date>/<TICKER>_analyze.json` | Deep analyze JSON (full fusion) |
| `data/output/research/<date>/watchlist_analyze.json` | Batch watchlist index |
| `data/output/research/<date>/<TICKER>_breakdown.md` | Agent breakdown markdown |
| `data/output/context/context_<date>.json` | Session cache (macro, market, geo) |
| `data/output/portfolio_backtests/<run_id>/summary.json` | Portfolio backtest KPIs |
| `data/output/portfolio_allocations/holdings_<date>.json` | Live allocation book |

All run outputs are **gitignored**.

---

## Documentation

| Resource | Contents |
|----------|----------|
| [docs/CHANGELOG.md](./docs/CHANGELOG.md) | **Release history** |
| [Trading-Journals/DailyCommands.md](./Trading-Journals/DailyCommands.md) | Daily operator commands |
| [docs/MYTRADINGSPACE_ONE_PAGER.md](./docs/MYTRADINGSPACE_ONE_PAGER.md) | Architecture one-pager |
| [docs/specs/INTELLIGENCE_DATA_PLAN.md](./docs/specs/INTELLIGENCE_DATA_PLAN.md) | Data sources & upgrade path |
| [docs/specs/PORTFOLIO_ENGINE.md](./docs/specs/PORTFOLIO_ENGINE.md) | Portfolio momentum engine |
| [docs/specs/FREE_DATA_SOURCES.md](./docs/specs/FREE_DATA_SOURCES.md) | Free API reference |
| [AGENTS.md](./AGENTS.md) | Cursor/agent instructions |
| [docs/SCRIPTS.md](./docs/SCRIPTS.md) | All scripts and engines |

---

## License

Project-specific license and maintainer notes live with the upstream repository settings.
