# MyTradingSpace — Daily Commands

> **Ship-it cheat sheet** · Repo root: `MyTradingSpace/` · Control plane: `./bin/mts`  
> Deep reference: [DailyTradingJournal.md](./DailyTradingJournal.md)

---

## First time only (new developer)

```bash


cp .env.example .env                        # add keys: POLYGON, FMP, FRED, OPENAI (optional)
python3 -m pip install -e .
cd apps/backtest-dashboard && npm install && cd ../..
```

---

## Every session (do this first)

```bash
cd MyTradingSpace
set -a && source .env && set +a             # load API keys
./bin/mts config validate                   # optional: validate .env schema
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


| URL                                                                              | Purpose                                             |
| -------------------------------------------------------------------------------- | --------------------------------------------------- |
| [http://localhost:3055/research/phoenix](http://localhost:3055/research/phoenix) | BUY/WATCH board + "Already up" extension column     |
| [http://localhost:3055/research/runs](http://localhost:3055/research/runs)       | Browse run outputs (pick newest `unified_master_`*) |
| [http://localhost:3055/research/signals](http://localhost:3055/research/signals) | Reconciled export (after `export`)                  |


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
./bin/mts analyze --ticker AAPL --fusion full --export-breakdown   # also writes data/output/research/<date>/AAPL_breakdown.md
./bin/mts analyze --ticker AAPL --fusion full --refresh-context    # bypass session cache (macro, market_summary, geopolitics)
./bin/mts analyze --ticker AAPL --fusion phoenix-fa --strategy-profile blend   # + Minervini/Moglen/Breitstein/McIntosh layers
./bin/mts strategy --ticker AAPL --date 2026-06-01 --profile minervini         # trader strategy layers only
./bin/mts export-breakdown --from-json path/to/analyze.json        # re-export markdown from saved JSON
./bin/mts sector --sector "Information Technology"   # one sector backtest (~50 tickers, faster than unified)
```

### Portfolio intelligence (momentum book — separate from daily)

```bash
./bin/mts portfolio backtest --start 2024-01-01 --end 2025-12-31 --budget 200000 --universe top10
./bin/mts portfolio allocate --budget 200000 --date 2026-06-13 --universe top10
./bin/mts portfolio allocate --budget 200000 --strategy-profile blend   # + Phoenix/strategy conviction enrich
# Fast full-agents (~3-5 min): parallel enrich on top 10 momentum names
./bin/mts portfolio allocate --budget 200000 --full-agents --enrich-max 10 --enrich-workers 8
```


| Output                                      | Path                                                                                 |
| ------------------------------------------- | ------------------------------------------------------------------------------------ |
| Backtest summary                            | `data/output/portfolio_backtests/<run_id>/summary.json`                              |
| Live allocation                             | `data/output/portfolio_allocations/holdings_<date>.json`                             |
| Dashboard (backtest KPIs + allocation book) | [http://localhost:3055/research/portfolio](http://localhost:3055/research/portfolio) |


Spec: [docs/specs/PORTFOLIO_ENGINE.md](../docs/specs/PORTFOLIO_ENGINE.md)

---

Eight agents: **Phoenix**, **Fundamental**, **Macro**, **Market Summary**, **News**, **Insider**, **Sentiment**, **Geopolitics**.


| Mode                 | Command                                        |
| -------------------- | ---------------------------------------------- |
| Standalone agent     | `./bin/mts agent <id> [--ticker X] [--date Y]` |
| Orchestrated session | `./bin/mts context --date Y`                   |


### Environment variables


| Key               | Used by                                                                   |
| ----------------- | ------------------------------------------------------------------------- |
| `POLYGON_API_KEY` | Phoenix, FA, Market Summary, News, Insider, Sentiment                     |
| `FMP_API_KEY`     | News, Insider, Geopolitics                                                |
| `FRED_API_KEY`    | Macro                                                                     |
| `OPENAI_API_KEY`  | *(optional)* LLM post-score bullets for News, Market Summary, Geopolitics |
| `LLM_ENABLED`     | All agents — `true` (default) or `false` to disable LLM everywhere        |


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

# Or refresh inline during full-fusion analyze (skips cached context file):
./bin/mts analyze --ticker AAPL --fusion full --refresh-context
```

### Disable LLM (deterministic-only mode)

```bash
LLM_ENABLED=false ./bin/mts agent geopolitics --date 2026-06-01
LLM_ENABLED=false ./bin/mts context --date 2026-06-01
```

---

## Where output lands


| Artifact        | Path                                                               |
| --------------- | ------------------------------------------------------------------ |
| Backtest        | `data/output/trading_runs/unified_master_<date>/master_pilot.json` |
| Export          | `data/output/trading_runs/phoenix_signals_reconciled.xlsx`         |
| Context session | `data/output/context/context_<date>.json`                          |
| LLM cache       | `data/output/llm_cache/` *(auto-cached, gitignored)*               |


> **Backtest labeling window:** 15 calendar days by default. Override with `--eval-days 30` to compare.

---

## Part 3 — Loop engineering (feature build + research ops)

Inspired by [loop engineering](https://addyosmani.com/blog/loop-engineering/). State lives in `.loop/state/` — not in model context.

### Feature loop (code delivery)

```bash
./bin/mts loop triage                    # rank FEAT-* backlog → .loop/state/queue.json
./bin/mts loop select                    # pick top auto-eligible feature
./bin/mts loop plan --feature FEAT-001   # write .loop/state/plans/FEAT-001.md
bash scripts/loop_spawn_worktree.sh FEAT-001   # isolated branch ../wt-FEAT-001
./bin/mts loop verify --feature FEAT-001 # pytest gate + verify artifact
./bin/mts loop cycle --dry-run           # full cycle without writes
```

Read first: `AGENTS.md`, `.loop/policies/risk-guardrails.md`, `.loop/policies/done-criteria.md`

Skills: `.loop/skills/*/SKILL.md` · Full scaffold: `skills/tradingagent-loop-engineering-scaffold.md`

### Research ops loop (read-only, no auto trades)

```bash
./bin/mts loop ops --date 2026-06-06
./bin/mts loop ops --date 2026-06-06 --refresh-context
# → data/output/research/<date>/ops_manifest.json
# → .loop/state/ops-journal.md
```

Human decision: use `--fusion full` + `agent_breakdown` — loop ops does not place trades.

### Loop state files


| File                             | Purpose                                |
| -------------------------------- | -------------------------------------- |
| `.loop/roadmap.yaml`             | Epics + features + auto_eligible flags |
| `.loop/state/queue.json`         | Ranked triage queue                    |
| `.loop/state/feature-journal.md` | Feature loop history                   |
| `.loop/state/ops-journal.md`     | Daily ops health                       |


