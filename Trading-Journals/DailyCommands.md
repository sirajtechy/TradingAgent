# MyTradingSpace — Daily Commands

> **Ship-it cheat sheet** · Repo root: `MyTradingSpace/` · Control plane: `./bin/mts`  
> Deep reference: [DailyTradingJournal.md](./DailyTradingJournal.md)

---

## First time only (new developer)

```bash
cd MyTradingSpace
cp .env.example .env                        # add keys: POLYGON, FMP, FRED, OPENAI (optional)
python3 -m pip install -e .
cd apps/backtest-dashboard && npm install && cd ../..
```

---

## Every session (do this first)

```bash
cd MyTradingSpace
set -a && source .env && set +a             # load API keys
```

---

## Part 1 — Production backtest (Phoenix + FA fusion)

### Daily production (run in this order)

```bash
./bin/mts daily                               # score all halal sectors (Phoenix+FA), write master_pilot.json, BUY excel, notify
./bin/mts export                              # refresh reconciled BUY/WATCH list for the dashboard
./bin/mts dashboard -b                        # open Research Lab in browser (background)
```

**Open in browser:**

| URL | Purpose |
|-----|---------|
| http://localhost:3055/research/phoenix | BUY/WATCH board + "Already up" extension column |
| http://localhost:3055/research/runs | Browse run outputs (pick newest `unified_master_*`) |
| http://localhost:3055/research/signals | Reconciled export (after `export`) |

```bash
./bin/mts stop                                # stop background dashboard when done
```

### Quick demo (one command, backtest + UI)

```bash
./bin/mts lab unified                         # full-universe backtest + dashboard (date defaults to yesterday)
```

### Spot checks (optional)

```bash
./bin/mts analyze --ticker AAPL               # single-ticker Phoenix+FA snapshot (JSON in terminal)
./bin/mts analyze --ticker AAPL --fusion full # all 8 agents → agent_breakdown + research_digest (you decide buy/hold/avoid)
./bin/mts sector --sector "Information Technology"   # one sector backtest (~50 tickers, faster than unified)
```

---

## Part 2 — Market intelligence agents (standalone + orchestrated)

Eight agents: **Phoenix**, **Fundamental**, **Macro**, **Market Summary**, **News**, **Insider**, **Sentiment**, **Geopolitics**.

| Mode | Command |
|------|---------|
| Standalone agent | `./bin/mts agent <id> [--ticker X] [--date Y]` |
| Orchestrated session | `./bin/mts context --date Y` |

### Environment variables

| Key | Used by |
|-----|---------|
| `POLYGON_API_KEY` | Phoenix, FA, Market Summary, News, Insider, Sentiment |
| `FMP_API_KEY` | News, Insider, Geopolitics |
| `FRED_API_KEY` | Macro |
| `OPENAI_API_KEY` | *(optional)* LLM post-score bullets for News, Market Summary, Geopolitics |
| `LLM_ENABLED` | All agents — `true` (default) or `false` to disable LLM everywhere |

### Session-level agents (market-wide, no ticker)

```bash
./bin/mts agent macro --date 2026-06-01                  # FRED: fed funds, CPI, unemployment, yield curve
./bin/mts agent market_summary --date 2026-06-01         # VIX, SPY, sector ETFs + macro composition
./bin/mts agent geopolitics --date 2026-06-01            # FMP general/forex news keyword scan + LLM classifier
```

### Ticker-level agents (require `--ticker`)

```bash
./bin/mts agent news --ticker AAPL --date 2026-06-01      # FMP headlines, analyst grades (GS/MS priority), price targets
./bin/mts agent insider --ticker AAPL --date 2026-06-01     # FMP insider trades: net activity, cluster buys, exec signals
./bin/mts agent sentiment --ticker AAPL --date 2026-06-01   # aggregator: news + insider + macro + geopolitics dimensions
```

### Orchestrated context session

Runs **macro → market_summary → geopolitics** and writes a single JSON file.

```bash
./bin/mts context --date 2026-06-01
# → data/output/context/context_2026-06-01.json
```

### Disable LLM (deterministic-only mode)

```bash
LLM_ENABLED=false ./bin/mts agent geopolitics --date 2026-06-01
LLM_ENABLED=false ./bin/mts context --date 2026-06-01
```

---

## Where output lands

| Artifact | Path |
|----------|------|
| Backtest | `data/output/trading_runs/unified_master_<date>/master_pilot.json` |
| Export | `data/output/trading_runs/phoenix_signals_reconciled.xlsx` |
| Context session | `data/output/context/context_<date>.json` |
| LLM cache | `data/output/llm_cache/` *(auto-cached, gitignored)* |

> **Backtest labeling window:** 15 calendar days by default. Override with `--eval-days 30` to compare.
