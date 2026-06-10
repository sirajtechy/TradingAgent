# MyTradingSpace — Project Journal

> **Go-to reference** · Control plane: `./bin/mts`  
> Daily ship-it commands → [DailyCommands.md](./DailyCommands.md)

---

## One-liner

Production trading agent = **Phoenix** (pattern/stage TA) + **Fundamental** (FA) fused 90/10 via orchestrator CWAF. Market intelligence layer = Macro + Market Summary + News + Insider + Geopolitics + Sentiment agents (standalone + orchestrated context session). Run sector/unified pilots → `data/output/trading_runs/` → Research Lab dashboard. Run context agents → `data/output/context/`. LLM post-score bullets (optional, deterministic fallback). Legacy technical/O'Neil/prediction agents archived 2026-06-01.

---

## What "monthly backtest" means here

Each run scores tickers **as of one signal date** (Phoenix + FA, no lookahead), fuses via **phoenix-fa** orchestrator CWAF, then **labels outcomes** over the next **`--eval-days`** calendar days (default **15**) using Polygon forward prices (target hit / exit reference). Engine: `agents/orchestrator/backtest_phoenix.py`, invoked by the sector/unified pilot scripts.

**Not the same as:** `./bin/mts analyze` — that is a single-ticker snapshot with no forward outcome labeling.

### Prerequisites (every backtest run)

```bash
cd MyTradingSpace
set -a && source .env && set +a    # POLYGON_API_KEY required for labeling
```

| Setting | Default | Notes |
|---------|---------|-------|
| Eval window | `--eval-days 15` | Forward target-hit labeling; use `--eval-days 30` to compare |
| Signal date | Yesterday | For `sector`, `unified`, `lab`, `analyze` |
| Daily date | Today | For `./bin/mts daily` |
| Global override | `./bin/mts --date YYYY-MM-DD <command>` | Applies to any subcommand |

### Halal sectors (exact names for `--sector`)

- Communication Services
- Consumer Discretionary
- Consumer Staples
- Energy
- Financials
- Health Care
- Industrials
- Information Technology
- Materials
- Real Estate
- Utilities

---

## Monthly backtest — all ways to run (production)

### Tier 1 — `./bin/mts` (preferred)

```bash
cd MyTradingSpace
set -a && source .env && set +a

# A. Single sector (first 50 tickers in sector JSON, phoenix-fa labeled window)
./bin/mts sector --sector "Information Technology" --date 2026-06-01
./bin/mts sector --sector "Energy" --date 2026-06-01 --eval-days 30
# → data/output/trading_runs/sector_information-technology_2026-06-01/master_pilot.json

# B. All sectors (full halal master list, parallel per sector)
./bin/mts unified --date 2026-06-01
./bin/mts unified --date 2026-06-01 --eval-days 30 --sector-jobs 11 --workers 8 --period-workers 2
# → data/output/trading_runs/unified_master_2026-06-01/master_pilot.json

# C. Backtest + Research Lab dashboard (starts dashboard in background)
./bin/mts lab sector --sector "Information Technology" --date 2026-06-01
./bin/mts lab unified --date 2026-06-01
./bin/mts lab sector --sector "Health Care" --date 2026-06-01 --no-dashboard   # backtest only
# → http://localhost:3055/research/phoenix
# → http://localhost:3055/research/runs

# D. Scheduled daily workflow (unified backtest + BUY excel + notify)
./bin/mts daily
./bin/mts daily --date 2026-06-01 --eval-days 30
./bin/mts daily --no-export-buy --no-telegram
```

### Tier 2 — `python -m pipelines` (same engines, explicit flags)

```bash
cd MyTradingSpace
set -a && source .env && set +a

python3 -m pipelines sector --sector "Information Technology" --signal-date 2026-06-01 --eval-days 30

python3 -m pipelines unified --signal-date 2026-06-01 --eval-days 30 \
  --sector-jobs 11 --workers 8 --period-workers 2

python3 -m pipelines daily --signal-date 2026-06-01 --eval-days 30
```

### Tier 3 — Direct pilot scripts (max control)

**Single-sector engine** — `scripts/backtests/run_halal_sector_month_pilot.py`

```bash
cd MyTradingSpace
set -a && source .env && set +a

# Full sector (all tickers in sector file)
python3 scripts/backtests/run_halal_sector_month_pilot.py \
  --sector "Information Technology" --full-sector \
  --signal-date 2026-06-01 --eval-days 30 \
  --single-master-json --workers 6 --period-workers 2 \
  --output-dir data/output/trading_runs/sector_information-technology_2026-06-01

# First N tickers (default limit=50 — same as ./bin/mts sector)
python3 scripts/backtests/run_halal_sector_month_pilot.py \
  --sector "Energy" --limit 50 --offset 0 \
  --signal-date 2026-06-01 --eval-days 30 --single-master-json \
  --output-dir data/output/trading_runs/sector_energy_2026-06-01

# Random sample (smoke / ablation)
python3 scripts/backtests/run_halal_sector_month_pilot.py \
  --sector "Financials" --limit 20 --random-sample --seed 42 \
  --signal-date 2026-06-01 --single-master-json \
  --output-dir data/output/trading_runs/smoke_financials_2026-06-01

# Explicit ticker list
python3 scripts/backtests/run_halal_sector_month_pilot.py \
  --tickers AAPL,MSFT,NVDA \
  --signal-date 2026-06-01 --eval-days 30 --single-master-json \
  --workers 3 --period-workers 1 \
  --output-dir data/output/trading_runs/tickers_aapl_msft_nvda_2026-06-01

# Batched checkpoints (long runs)
python3 scripts/backtests/run_halal_sector_month_pilot.py \
  --sector "Industrials" --full-sector --batch-size 25 \
  --signal-date 2026-06-01 --eval-days 30 \
  --output-dir data/output/trading_runs/industrials_batched_2026-06-01
```

**All-sector parallel engine** — `scripts/backtests/run_master_data_parallel_pilot.py`

```bash
cd MyTradingSpace
set -a && source .env && set +a

# Same as ./bin/mts unified (staging dir cleaned after merge)
python3 scripts/backtests/run_master_data_parallel_pilot.py \
  --signal-date 2026-06-01 --eval-days 30 \
  --master-json data/input/master_data/halal_tickers_clean.json \
  --output-root data/output/_staging_unified_master_2026-06-01 \
  --merged-output data/output/trading_runs/unified_master_2026-06-01/master_pilot.json \
  --sector-jobs 11 --workers 8 --period-workers 2 \
  --cleanup-staging

# Re-merge only (pilots already finished under output-root)
python3 scripts/backtests/run_master_data_parallel_pilot.py \
  --signal-date 2026-06-01 --skip-pilot \
  --output-root data/output/_staging_unified_master_2026-06-01 \
  --merged-output data/output/trading_runs/unified_master_2026-06-01/master_pilot.json
```

### Tier 4 — Dev / smoke (not full universe backtests)

```bash
cd MyTradingSpace
set -a && source .env && set +a

# Single ticker, fused snapshot only (no forward labeling)
./bin/mts analyze --ticker AAPL --date 2026-06-01 --fusion phoenix-fa
./bin/mts analyze --ticker AAPL --date 2026-06-01 --fusion phoenix      # Phoenix only
./bin/mts analyze --ticker AAPL --date 2026-06-01 --fusion fundamental  # FA only

# One ticker, one labeled window (calls backtest_phoenix directly)
python3 -c "
from datetime import date, timedelta
from agents.orchestrator.backtest_phoenix import run_monthly_backtest
sig = date.fromisoformat('2026-06-01')
end = sig + __import__('datetime').timedelta(days=30)
print(run_monthly_backtest('AAPL', months=[(sig, end)], period_workers=1))
"
```

---

## Market intelligence agents — standalone + orchestrated

### Agent inventory

| Agent | ID | Scope | Data source | CLI |
|-------|----|-------|-------------|-----|
| **Macro** | `macro` | Session (market-wide) | FRED (fed funds, CPI, unemployment, yield curve) | `./bin/mts agent macro --date` |
| **Market Summary** | `market_summary` | Session (market-wide) | Polygon (VIX, SPY, sector ETFs) + Macro internally | `./bin/mts agent market_summary --date` |
| **Geopolitics** | `geopolitics` | Session (market-wide) | FMP general/forex news + keyword scan + LLM classifier | `./bin/mts agent geopolitics --date` |
| **News Analyst** | `news` | Ticker | FMP (headlines, analyst grades GS/MS priority, price targets) | `./bin/mts agent news --ticker X --date` |
| **Insider Trades** | `insider` | Ticker | FMP (insider filings: net activity, cluster buys, exec signals) | `./bin/mts agent insider --ticker X --date` |
| **Sentiment** | `sentiment` | Ticker (aggregator) | Consumes news + insider + macro + geopolitics scores | `./bin/mts agent sentiment --ticker X --date` |

### Environment variables

| Key | Required by | Notes |
|-----|-------------|-------|
| `POLYGON_API_KEY` | Phoenix, FA, Market Summary, News, Insider, Sentiment | Core data |
| `FMP_API_KEY` | News, Insider, Geopolitics | Financial Modeling Prep |
| `FRED_API_KEY` | Macro | St. Louis FRED |
| `OPENAI_API_KEY` | *(optional)* News, Market Summary, Geopolitics | LLM post-score bullets only |
| `LLM_ENABLED` | All (default: `true`) | Set `false` for fully deterministic mode |
| `LLM_MODEL` | *(optional, default: `gpt-4o-mini`)* | OpenAI-compatible model |

### Running standalone agents

```bash
cd MyTradingSpace
set -a && source .env && set +a

# Session-level (no ticker needed)
./bin/mts agent macro --date 2026-06-07
./bin/mts agent market_summary --date 2026-06-07
./bin/mts agent geopolitics --date 2026-06-07

# Ticker-level
./bin/mts agent news --ticker AAPL --date 2026-06-07
./bin/mts agent insider --ticker AAPL --date 2026-06-07
./bin/mts agent sentiment --ticker AAPL --date 2026-06-07

# Deterministic-only (no LLM calls)
LLM_ENABLED=false ./bin/mts agent news --ticker AAPL --date 2026-06-07
```

### Running orchestrated context session

```bash
./bin/mts context --date 2026-06-07
# → data/output/context/context_2026-06-07.json
```

### LLM strategy (post-score only)

- LLM is **never** used for scoring — all scores are deterministic rule-based
- LLM is called **after** scoring to generate human-readable bullets and sentiment labels
- Agents with LLM enrichment: **News** (headline sentiment), **Market Summary** (daily briefing), **Geopolitics** (risk classification)
- Cache: `data/output/llm_cache/` (content-hash keyed, gitignored)
- Disable globally: `LLM_ENABLED=false` or `--llm off` — scores unchanged, bullets fall back to rule-based

### Agent architecture

Each agent lives in `agents/<id>/` with these standard files:

| File | Role |
|------|------|
| `config.py` | Settings dataclass + `load_settings()` |
| `models.py` | Request/snapshot dataclasses |
| `data_client.py` / `fmp_client.py` / `fred_client.py` | Agent-local data fetcher |
| `rules.py` | Deterministic scoring (subscores → weighted composite → signal/band) |
| `graph.py` | LangGraph pipeline: fetch → [classify] → evaluate → [enrich_llm] → render |
| `service.py` | Public `analyze_market()` or `analyze_ticker()` entry point |
| `reporting.py` | Text report builder |
| `adapter.py` | Re-exports `envelope_from_<id>` from orchestrator |

Shared: `agents/_shared/llm_summary.py` (post-score LLM helper with cache + kill-switch)

### Agent envelope contract

Every agent produces a standardized envelope via `agents/orchestrator/agent_envelope.py`:

```json
{
  "agent_id": "...",
  "as_of_date": "...",
  "signal": "...",
  "score": 0,
  "confidence": "...",
  "band": "...",
  "abstain": false,
  "reason": null,
  "data_quality": "...",
  "warnings": [],
  "extras": {
    "bullets": [],
    "subscores": {},
    "data_sources": []
  }
}
```

Registry: `agents/_registry.py` — maps `agent_id` → (analyze fn, envelope fn)

---

## After a backtest — view & export

```bash
cd MyTradingSpace

./bin/mts dashboard -b          # or: ./bin/mts stop && ./bin/mts dashboard -b
./bin/mts export --from 2026-06-01 --to 2026-06-01   # reconciled BUY/WATCH across runs
```

| Dashboard URL | Purpose |
|---------------|---------|
| http://localhost:3055/research/phoenix | BUY/WATCH board |
| http://localhost:3055/research/runs | Browse run outputs |
| http://localhost:3055/research/signals | Reconciled export *(after `export`)* |

---

## Output artifacts (where results land)

| Run type | Primary artifact |
|----------|------------------|
| `./bin/mts sector` | `data/output/trading_runs/sector_<slug>_<date>/master_pilot.json` |
| `./bin/mts unified` / `daily` | `data/output/trading_runs/unified_master_<date>/master_pilot.json` |
| Direct sector pilot (no `--single-master-json`) | `run_bundle.json`, `per_ticker/`, `confusion_matrix.json` under `--output-dir` |
| `daily` BUY export | `data/output/trading_runs/phoenix_buy_<date>.xlsx` |
| `./bin/mts context` | `data/output/context/context_<date>.json` |
| `./bin/mts agent <id>` | JSON printed to stdout |
| LLM cache | `data/output/llm_cache/<agent>_<date>_<hash>.json` *(gitignored)* |

Each `master_pilot.json` includes per-ticker fusion signals, entry/exit references, target-hit flags, and a confusion matrix summary.

---

## Active layout (what matters daily)

| Folder | Role |
|--------|------|
| `bin/mts`, `cli/` | User commands (`daily`, `sector`, `unified`, `analyze`, `agent`, `context`) |
| `pipelines/` | analyze, sector, unified, daily → backtest.py |
| `agents/phoenix`, `fundamental` | Core scoring agents (Phoenix TA + FA) |
| `agents/macro`, `market_summary` | Session-level intelligence (FRED + Polygon market) |
| `agents/news`, `insider` | Ticker-level intelligence (FMP data) |
| `agents/sentiment` | Multi-dimension aggregator (news + insider + macro + geopolitics) |
| `agents/geopolitics` | Geopolitical risk scanner (FMP news + LLM) |
| `agents/_shared/` | Shared LLM helper (`llm_summary.py`) |
| `agents/orchestrator` | Fusion (CWAF), backtest, envelopes |
| `agents/polygon_data` | Polygon.io data client |
| `core/` | universe, export, contracts, paths |
| `apps/backtest-dashboard/` | Research Lab UI |
| `data/output/trading_runs/` | Backtest outputs *(gitignored)* |
| `data/output/context/` | Agent context session outputs *(gitignored)* |
| `data/output/llm_cache/` | LLM response cache *(gitignored)* |
| `docs/specs/` | Agent specs + template |
| `tests/` | Unit tests per agent phase |
| `archive/` | Retired agents/scripts — not for daily use |

> Retired 2026-06-01: `archive/agents/technical`, `oneil`, `prediction`, `orchestrator-ta-fa`.

---

## Refactor log (high level)

| Date | Change |
|------|--------|
| 2026-06 | `bin/mts` control plane; Research Lab; export; `apps/` move; engine shrink; docs under `docs/` |
| 2026-06 | Agent cleanup: Phoenix+FA only; technical/oneil/prediction archived |
| 2026-06 | Verified lab sector IT 2026-06-01: 50 tickers, 32 WATCH, 16 AVOID, ~82s |
| 2026-06-07 | Phase A: Macro + Market Summary agents (FRED + Polygon VIX/SPY/ETFs) |
| 2026-06-07 | Phase B: News + Insider + Sentiment agents (FMP headlines/grades/insider trades) |
| 2026-06-07 | Phase C: Geopolitics agent + shared LLM helper + LLM wired into news/market_summary |

**Pending:** Phase D standalone CLI polish · Phase E full fusion (additive) · Phase F dashboard + docs

---

## Journal entries

| Date | Entry |
|------|-------|
| 2026-06-01 | Retired agents technical/oneil/prediction + ta-fa path; established this file as project journal |
| 2026-06-01 | Documented full monthly backtest command matrix (mts / pipelines / direct pilots / dev smoke) |
| 2026-06-01 | `eval_days` default 30→15; Phoenix `extension_guardrail` (5d/4w chase metrics + dashboard Chase column); Upside T1 label fix |
| 2026-06-01 | Dashboard "Already up" column + Trade focus filter (BUY + WATCH score>60); `extension_justification` in master_pilot |
| 2026-06-04 | Dashboard default run fix: was loading stale `sector_energy_2025` run; now defaults to newest `unified_master_*`; amber banner when run predates guardrails |
| 2026-06-04 | Git branch `feature/phoenix-chase-guardrail-eval-15d` — ships agent archive, phoenix-fa-only, eval_days=15, extension guardrail + Already up UI, bin/mts control plane, Research Lab |
| 2026-06-04 | Added `Trading-Journals/` in git; README curated for Phoenix+FA, eval_days=15, extension UI |

---

## Market intelligence agents — build log (2026-06-07)

### Phase A — Macro + Market Summary

- Built `agents/macro/` (8 files): FRED client → fed funds, CPI YoY, unemployment, yield spread → deterministic scoring → LangGraph pipeline
- Built `agents/market_summary/` (8 files): Polygon VIX/SPY/sector ETFs + macro composition → market-wide signal
- Envelope adapters + registry + CLI (`./bin/mts agent macro|market_summary`)
- Context command: `./bin/mts context` runs session agents → `data/output/context/`
- 4 unit tests (FRED parsing, CPI YoY, macro scoring, VIX capping)

### Phase B — News + Insider + Sentiment

- Built `agents/news/` (8 files): FMP headlines + analyst grades (GS/MS priority) + price targets
- Built `agents/insider/` (8 files): FMP insider trades → net activity / cluster buys / executive signal scoring
- Built `agents/sentiment/` (8 files): Aggregator consuming news + insider + macro + geopolitics dimension scores
- All point-in-time safe: `publishedDate` / `filingDate` ≤ `as_of_date`
- CLI: `./bin/mts agent news|insider|sentiment --ticker X --date Y`
- 10 unit tests (upgrades bullish, net buys/sells, date parsing, sentiment composition, abstain)

### Phase C — Geopolitics + LLM helper

- Built `agents/_shared/llm_summary.py`: OpenAI-compatible post-score narrative generator; content-hash cache in `data/output/llm_cache/`; kill-switch `LLM_ENABLED=false`
- Built `agents/geopolitics/` (8 files): FMP general + forex news scan → 20+ keyword pre-filter → keyword density (45%) + headline concentration (30%) + LLM classification (25%, bounded ±8pt)
- Wired LLM into News + Market Summary — post-score only, never mutates scores
- Geopolitics wired into Sentiment agent as 5th dimension
- Context session updated: macro + market_summary + geopolitics
- 9 unit tests; **23 tests passing** across 3 test files

---

## Shipped in `feature/phoenix-chase-guardrail-eval-15d` (2026-06-04)

### Backtest labeling

- Default forward eval window 30 → 15 calendar days (`--eval-days` still overridable)
- TP/FP unchanged logic: bullish fusion + Target 1 hit within eval window

### Phoenix extension guardrail (signal date only, no future Polygon)

- New `agents/phoenix/extension.py` → `extension_guardrail` on every analyze/backtest row
- Fields: `justification`, `chase_risk`, 5d/10d/4w %, vs SMA20, vs pivot
- BUY signal unchanged; warnings only

### Dashboard (`/research/phoenix`)

- Columns: Px score, **Already up** (justification), 5d %, 4w %, Chase
- **Already up** shown for all BUY; WATCH only when Phoenix score > 60
- Filter: **Trade focus** = BUY + WATCH score>60
- Default run: newest `unified_master_*/master_pilot.json`
- Renamed Upside T1/T2 (not "already rallied")

### Agent cleanup

- Removed from production: `technical/`, `oneil/`, `prediction/`, ta-fa orchestrator path → `archive/agents/`
- Production stack: Phoenix + FA fusion only

**Verify after pull:**

```bash
./bin/mts lab unified --date YYYY-MM-DD
# Dashboard → unified_master_<date> → check "Already up" column
```

---

## Remaining phases

### Phase D — Standalone CLI polish (no fusion yet)

- Verify all `./bin/mts agent <id>` commands end-to-end with live API keys
- Optional context cache JSON improvements

### Phase E — Additive full fusion

- New `agents/orchestrator/fusion_full.py` (does not replace `fusion_phoenix.py`)
- `FusionMode.FULL_CONTEXT` in `modes.py`
- Extend `pipelines/analyze.py` with opt-in `--fusion full` (default remains `phoenix-fa`)
- Weights: Phoenix 55%, FA 10%, macro 10%, news 10%, insider 8%, geopolitics 7%
- `market_summary` as regime overlay

### Phase F — Dashboard + docs

- New route `/research/context` (reads context JSON)
- Optional Phoenix table columns from agent extras
- Update README + Trading-Journals
- CI: smoke each agent
