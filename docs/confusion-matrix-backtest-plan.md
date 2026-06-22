# Confusion Matrix Backtest Plan — Phoenix + Strategies + Full Fusion

**Status:** Active design (documentation phase)  
**Last updated:** 2026-06-19  
**Goal:** A **resilient, multi-layer confusion matrix framework** that maximizes interpretable true positives from Phoenix + 4 trader strategies + fundamental fusion + intelligence agents, without lookahead bias.

Related specs:
- `docs/planned-unified-technical-agent.md` — **Technical Agent facade** (Phoenix + 4 strategies), enrichment gating, matrix layers A0–D
- `docs/planned-atr-sma50-exit-ladder.md`
- `docs/planned-151-trading-strategies.md`

---

## Executive summary

Today the repo has a **working 2×2 confusion matrix** for **Phoenix + FA fusion** on sector/month pilots (`confusion_matrix.json`, Research Lab `/trading-runs`). It does **not** yet evaluate:

- Individual intelligence agents (macro, news, sentiment, insider, geopolitics)
- The 4 strategy modules (Minervini, Moglen, Breitstein, McIntosh) or `blend` meta-signals
- Full-context fusion (`fusion_full`)
- Walk-forward stability vs single-date snapshots
- Matthews Correlation Coefficient (MCC) or multi-threshold operating points

This plan defines ground truth, prediction layers, per-agent matrices, fused matrices, implementation phases, and reuse vs greenfield work.

---

## Current infrastructure (investigation summary)

### Confusion matrix code (reuse)

| Location | Role |
|----------|------|
| `core/universe/__init__.py` | `empty_matrix()`, `update_matrix()`, `matrix_metrics()` — TP/FP/TN/FN, precision, recall, F1, specificity, abstention |
| `agents/orchestrator/backtest_phoenix.py` | Monthly period runner; `_correctness_for_signal()`; Phoenix + FA only; target-hit ground truth |
| `scripts/backtests/run_halal_sector_month_pilot.py` | Canonical labeled window backtest → `confusion_matrix.json`, `run_bundle.json`, `pilot_manifest.json` |
| `scripts/backtests/run_master_data_parallel_pilot.py` | All-sector parallel wrapper |
| `scripts/lib/run_bundle.py` | Stable bundle schema for Research Lab; `evaluation.signal_correct` on rows |
| `apps/backtest-dashboard/app/lib/confusionBucket.ts` | UI bucket helpers for `/trading-runs`, phoenix-watch-buy sort |
| `archive/scripts/legacy-dashboard/generate_agent_reports.py` | 3×3 matrix + misclassification reports (TA/FA/orchestrator) — reference only |

### Signal production paths

**Phoenix**

- Entry: `agents/phoenix/service.py` → `analyze_ticker(ticker, as_of_date=...)`
- Data: `agents/phoenix/data_client.py` — Polygon 500 daily bars ending ≤ `as_of_date` (PIT-safe when Polygon configured)
- Output: `signal` (BUY/WATCH/AVOID), scores, `trade_levels`, stage, VCP, extension/chase context

**4 strategy modules**

- Entry: `agents/strategies/service.py` → `analyze_strategies(..., profile=blend|minervini|...)`
- Context: `build_context()` pulls Phoenix snapshot + optional FA + SPY via same Polygon PIT client
- Per-module: `agents/strategies/{minervini,moglen,breitstein,mcintosh}/service.py`
- Meta: `agents/strategies/fusion.py` → `build_meta_signals()` (e.g. `high_conviction_swing`, `consensus_entry_triggers`)

**Fundamental**

- Entry: `agents/fundamental/service.py` with `as_of_date`
- PIT: FMP/yfinance clients filter statements/dividends by `filing_date <= as_of_date`; price via Polygon

**Orchestrator fusion**

| Mode | Module | Weights (default) |
|------|--------|-------------------|
| `phoenix_fund` (production) | `agents/orchestrator/fusion_phoenix.py` | ~90% Phoenix / 10% FA CWAF |
| `full_context` (Research Lab) | `agents/orchestrator/fusion_full.py` | phoenix, fundamental, macro, news, insider, geopolitics via `OrchestratorSettings.full_context_weights` |
| Dispatch | `agents/orchestrator/modes.py` → `fuse_by_mode()` | |

**Full analyze pipeline:** `agents/orchestrator/pipeline_full.py` runs all agents + `build_agent_breakdown()`.

### Backtest entry points

| Command / script | Output |
|------------------|--------|
| `./bin/mts sector --sector "…" --date YYYY-MM-DD` | `data/output/trading_runs/sector_<slug>_<date>/` |
| `./bin/mts unified --date YYYY-MM-DD` | `unified_master_<date>/master_pilot.json` |
| `./bin/mts daily` | Production backtest + exports |
| `python scripts/run_trading.py backtest --engine halal-sector-pilot -- …` | Same as sector pilot |
| `./bin/mts portfolio backtest --start … --end …` | Portfolio rotation KPIs (not Phoenix BUY matrix) |
| `archive/backtests/run_{fundamental,technical,orchestrator,oneil}.py` | Legacy sector matrices |
| `archive/scripts/backtests-legacy/` | Year-titled Phoenix+orchestrator studies |

Playbook: `docs/BACKTEST_PLAYBOOK.md` · Output schema: `docs/BACKTEST_OUTPUT_FORMAT.md`

---

## Temporal safety — can agents pull archival data when backtesting backward?

**Short answer:** Price/Phoenix/FA/macro(FRED)/insider(EDGAR)/Finnhub news are **designed for point-in-time** when `as_of_date` is passed. **yfinance news/insider/geopolitics feeds are not true historical archives** — they return *today’s* snapshot filtered by publish date, so deep historical backtests will have **missing or biased** intelligence data (not necessarily lookahead, but **not reproducible archival**).

### Per-agent assessment

| Agent | Primary client | PIT-safe for historical `as_of_date`? | Notes |
|-------|----------------|--------------------------------------|-------|
| **Phoenix** | Polygon `fetch_daily_bars` ≤ as_of | **Yes** (with Polygon key) | yfinance fallback less strict; documented in playbook |
| **Fundamental** | FMP / yfinance + filing_date filter | **Mostly yes** | Restatement/revision risk on yfinance; FMP preferred. Price PIT via Polygon |
| **Macro** | FRED `observation_end=as_of_date` | **Yes** | yfinance ^TNX/^IRX proxy filters `index.date <= as_of_date` |
| **News** | FMP | **Partial** | API fetches latest batch; client filters `pub <= as_of_date`. Works for recent history; **deep history incomplete** |
| **News** | Finnhub `/company-news` with start/end | **Yes** (API archival) | Preferred for historical news backtests |
| **News** | yfinance `.news` | **No (archival)** | Current Yahoo feed only; date filter cannot recover missing old headlines |
| **Insider** | SEC EDGAR Form 4 | **Yes** | Filings + transaction dates filtered ≤ as_of; filing index is historical |
| **Insider** | yfinance insider df | **No (archival)** | Current table snapshot; filtered by date but incomplete for past dates |
| **Insider** | FMP | **Partial** | Same “fetch recent, filter” pattern as news |
| **Sentiment** | Derived (news, insider, macro, geo, optional price) | **Inherited** | Only as PIT-safe as upstream; label **Derived** in dashboard |
| **Geopolitics** | FMP general/forex | **Partial** | Client-side date filter on latest fetch |
| **Geopolitics** | yfinance ETF news scan | **No (archival)** | Current feed + keyword filter |
| **4 strategies** | Phoenix Polygon snapshots | **Yes** | Same OHLCV path as Phoenix |
| **Session context cache** | `data/output/context/context_<date>.json` | **Risk** | Stale cache if keys/sources change; use `--refresh-context` for historical reruns |

**Production backtest today (`backtest_phoenix.py`):** Runs **Phoenix + FA only** — intelligence agents are **not** in the sector pilot confusion matrix. Full fusion historical backtest is **not yet run** (`docs/MYTRADINGSPACE_ONE_PAGER.md` gap list).

**Recommendation for resilient backtests:** Require manifest flags: `data_sources`, `pit_safe: true|false` per agent, and **disable or abstain** agents whose primary source is yfinance news/insider when `as_of_date` < (today − 30d).

---

## Definitions — ground truth vs predictions

### Ground truth labels (outcome — uses post-cutoff data only)

Implement as pluggable **LabelSpec** (default + alternatives):

| Label ID | Definition | bullish “positive class” | Used when |
|----------|------------|--------------------------|-----------|
| `target_hit_1m` **(current default)** | Phoenix `target_1` (or +5% fallback) touched on high within `[signal_date, result_date]` | Hit = TP for bullish pred | Sector/month pilot |
| `forward_return_1m` | Close at result_date vs entry: return ≥ +X% | Alternative for strategy research |
| `max_favorable_excursion` | Max high in window ≥ entry × (1 + X%) | Swing hold studies |
| `atr_peak_ge_7` | Peak `(Close-SMA50)/ATR14` in leg ≥ 7 before stop | Exit-ladder research (deferred) |
| `stop_before_target` | Stop hit before target | Risk-focused FN analysis |

**Actual direction mapping (current 2×2):**

```
bullish prediction + target_hit=True  → TP
bullish prediction + target_hit=False → FP
bearish prediction + target_hit=False → TN
bearish prediction + target_hit=True  → FN
neutral / missing outcome             → abstention bucket (not in 2×2 denominator)
```

Source: `_correctness_for_signal()` in `agents/orchestrator/backtest_phoenix.py`.

### Prediction signals (cutoff-date only)

Map all agents to **`{bullish, bearish, neutral}`** via existing extractors:

| Layer | Source field | Extractor |
|-------|--------------|-----------|
| Phoenix | `signal` BUY/WATCH/AVOID | `_phoenix_direction()` in run_bundle; `_extract_phoenix_output()` |
| Fundamental | experimental_score band | `BAND_TO_SIGNAL` |
| Fusion (phoenix-fa) | `fusion.final_signal` | `fuse_signals_phoenix()` |
| Fusion (full) | `fusion.final_signal` | `fuse_signals_full()` |
| Macro / News / Insider / Geo | envelope `direction` or score thresholds | `envelope_to_agent_output()` |
| Sentiment | composite score bands | `agents/sentiment/rules.py` |
| Minervini / Moglen / Breitstein / McIntosh | `signal` + `entry_trigger` | StrategySignal; optional **trigger-only** positive class |
| Strategy blend | `meta_signals.high_conviction_swing`, `consensus_entry_triggers` | Custom binary predictors |

**Operating points (for “many true positives” tuning):**

- Phoenix: treat WATCH as bullish (recall↑) vs BUY-only (precision↑)
- Strategies: score ≥ threshold OR `entry_trigger=True`
- Fusion: require N-of-M agent agreement before bullish call

Document chosen threshold in `pilot_manifest.json` → `prediction_spec`.

---

## Architecture — resilient multi-matrix framework

```
                    ┌─────────────────────────────────────┐
                    │  BacktestGrid (dates × tickers)      │
                    │  walk-forward OR single-window       │
                    └─────────────────┬───────────────────┘
                                      │
          cutoff as_of_date ──────────┼────────── result_date (outcome only)
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  SignalCollector                     │
                    │  phoenix, fa, 4 strategies, intel    │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    ▼                                     ▼
         ┌──────────────────┐                 ┌──────────────────┐
         │  FusionEngine     │                 │  PerAgent preds   │
         │  phoenix-fa       │                 │  (no fusion)      │
         │  full_context     │                 └────────┬─────────┘
         └────────┬─────────┘                          │
                  │                                      │
                  └──────────────┬───────────────────────┘
                                 ▼
                    ┌─────────────────────────────────────┐
                    │  OutcomeEvaluator (LabelSpec)        │
                    │  Polygon forward window              │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  ConfusionMatrixBuilder              │
                    │  per agent + fused + meta-strategy   │
                    │  + sector rollup + walk-forward agg  │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  Artifacts                           │
                    │  confusion_matrix.json (extended)    │
                    │  misclassification.json              │
                    │  run_bundle.json / master_pilot.json │
                    └─────────────────────────────────────┘
```

### Extended `confusion_matrix.json` schema (proposed v2)

```json
{
  "schema_version": "2.0.0",
  "label_spec": "target_hit_1m",
  "prediction_spec": { "phoenix": "BUY_ONLY", "fusion_mode": "phoenix_fund" },
  "pit_manifest": { "macro": "fred", "news": "finnhub", "insider": "edgar" },
  "overall": { "TP": 0, "FP": 0, "TN": 0, "FN": 0, "metrics": {} },
  "by_agent": {
    "phoenix": { "matrix": {}, "metrics": {} },
    "fundamental": {},
    "fusion_phoenix_fa": {},
    "fusion_full": {},
    "minervini": {},
    "moglen": {},
    "breitstein": {},
    "mcintosh": {},
    "strategy_blend": {},
    "macro": {},
    "news": {},
    "insider": {},
    "sentiment": {},
    "geopolitics": {}
  },
  "by_sector": {},
  "walk_forward": {
    "windows": [],
    "stability": { "precision_std": null, "recall_std": null }
  }
}
```

### Metrics (per matrix)

| Metric | Formula | When to prioritize |
|--------|---------|-------------------|
| **Precision** | TP / (TP+FP) | Minimize false BUYs |
| **Recall** | TP / (TP+FN) | Maximize captured winners (user goal) |
| **F1** | harmonic mean | Balance |
| **Specificity** | TN / (TN+FP) | Bearish / avoid quality |
| **Accuracy** | (TP+TN) / directional | Overall; misleading if class imbalance |
| **MCC** | (TP×TN − FP×FN) / √((TP+FP)(TP+FN)(TN+FP)(TN+FN)) | **Imbalanced abstention-heavy runs** — not in repo yet |
| **Abstention rate** | neutral / all periods | Coverage vs confidence tradeoff |

Add **`mcc`** to `matrix_metrics()` in Phase 2.

### Misclassification artifact

Per FP/FN row (extends archive `generate_agent_reports.py`):

- ticker, sector, signal_date, predicted, actual (target_hit), agent layer
- Phoenix stage, extension ATR, strategy triggers active
- data_sources + pit_safe flags
- root_cause tag: `chase_extended`, `fa_conflict`, `macro_headwind`, `missing_news_archive`, etc.

---

## Walk-forward vs single-date backtest

| Mode | Description | Use case |
|------|-------------|----------|
| **Single-window** | One `--signal-date` + fixed horizon (current halal-sector-pilot) | Fast sector snapshot, dashboard bundle |
| **Monthly grid** | `run_monthly_backtest()` periods per ticker | Current Phoenix+FA engine |
| **Walk-forward** | Train thresholds on window A, evaluate on B; roll | Prevent threshold overfit; **Phase 4** |
| **Portfolio rebalance dates** | Align with FRR 21st + regime weekly | Portfolio × signal matrix cross-check |

Walk-forward protocol (proposed):

1. Split timeline into 6-month train / 3-month test folds.
2. On train: sweep Phoenix WATCH inclusion, fusion weights, strategy trigger thresholds → maximize MCC with min recall floor.
3. On test: freeze params; record matrix per fold.
4. Report mean ± std precision/recall/MCC in `walk_forward.stability`.

---

## Implementation phases

### Phase 1 — Extend existing pilot (low risk) ✅ design target first code

**Files:** `agents/orchestrator/backtest_phoenix.py`, `scripts/backtests/run_halal_sector_month_pilot.py`

- Add parallel **per-agent signal capture** on same periods (Phoenix-only matrix already exists as `signal_correct_phoenix`).
- Add **fundamental-only** correctness column.
- Emit **`by_agent.phoenix` / `by_agent.fundamental` / `by_agent.fusion`** in `confusion_matrix.json`.
- Add **`mcc`** to `core/universe/matrix_metrics()`.

### Phase 2 — Strategy layer

**Files:** new `agents/orchestrator/backtest_strategies.py` or extend `backtest_phoenix.py`

- Call `analyze_strategies(..., fetch_market_data=False)` reusing cached Phoenix/FA from period.
- Matrices for each of 4 modules + `strategy_blend` meta predictors.
- Optional **`entry_trigger`** as binary predictor (high recall for swing entries).

### Phase 3 — Full fusion + intelligence agents

**Files:** `agents/orchestrator/pipeline_full.py`, new `agents/orchestrator/backtest_full.py`

- Run `pipeline_full` per period with PIT manifest.
- **Abstain** agents failing PIT check (yfinance news on old dates).
- Matrices for macro, news, insider, sentiment, geopolitics + `fusion_full`.
- Compare **`phoenix_fa` vs `full_context`** recall/precision tradeoff.

### Phase 4 — Research Lab + exit ladder labels

**Files:** `apps/backtest-dashboard/`, `docs/planned-atr-sma50-exit-ladder.md`

- Dashboard: multi-agent matrix heatmap on `/research/runs` and sector compare.
- Optional **`atr_peak_ge_7`** label spec for exit research.
- Misclassification panel wired to new `misclassification.json`.

### Phase 5 — Walk-forward + CI

- Parameter sweep CLI; store winning specs in `data/config/backtest_specs/`.
- GitHub Action: one sector smoke + matrix regression bounds.

---

## Reuse vs build

| Component | Reuse | Build |
|-----------|-------|-------|
| 2×2 matrix math | `core/universe/` | MCC, multi-class 3×3 optional |
| Period runner | `backtest_phoenix.py` | Multi-agent collector, strategy hooks |
| Sector pilot CLI | `run_halal_sector_month_pilot.py` | Extended JSON schema v2 |
| Bundle / dashboard | `run_bundle.py`, `confusionBucket.ts` | Multi-agent columns, compare view |
| Full agent run | `pipeline_full.py` | Historical loop + PIT gating |
| Misclassification reports | `archive/.../generate_agent_reports.py` | Port patterns to `core/evaluation/misclass.py` |
| Intelligence archival | Finnhub, FRED, EDGAR clients | yfinance abstain policy; FMP date-range params if available |
| Walk-forward | — | New `core/evaluation/walk_forward.py` |
| ATR exit labels | Phoenix extension | Deferred per exit-ladder doc |

---

## Operator checklist (historical backtest)

1. Set `POLYGON_API_KEY`, `FRED_API_KEY`, `FINNHUB_API_KEY`, `SEC_EDGAR_USER_AGENT`.
2. Pass explicit `--signal-date` / `--date` — never silent “today”.
3. Pin universe: `data/halal_universe/halal_sector_tickers.json`.
4. For dates > 30 days ago: set `NEWS_DATA_SOURCE=finnhub`, `INSIDER_DATA_SOURCE=edgar`; expect sentiment to inherit PIT quality.
5. Write `pilot_manifest.json` with `no_lookahead_statement` + per-agent `pit_manifest`.
6. Compare runs via Research Lab `/trading-runs` compare picker.

---

## Success criteria (user intent: “many true positives”)

1. **Recall** on fused bullish calls ≥ baseline Phoenix-only (measure on same universe/ dates).
2. **Precision** must not collapse — track MCC when tuning for recall.
3. Per-agent matrices identify **which layer adds TP** without adding FP (attribution).
4. Walk-forward stability: precision/recall std below agreed threshold across folds.
5. Zero lookahead violations in manifest audit (automated test in Phase 5).

---

## References

- `docs/BACKTEST_PLAYBOOK.md` — no-lookahead, universe pinning
- `docs/BACKTEST_OUTPUT_FORMAT.md` — row-level outcome fields
- `docs/MYTRADINGSPACE_ONE_PAGER.md` — sector commands, gap list
- `docs/specs/ORCHESTRATOR_MODES.md` — fusion modes
- `docs/specs/INTELLIGENCE_DATA_PLAN.md` — agent data legitimacy
- `agents/orchestrator/backtest_phoenix.py` — current ground truth
- `scripts/backtests/run_halal_sector_month_pilot.py` — canonical pilot
