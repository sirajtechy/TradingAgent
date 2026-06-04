# Backtest Playbook

This playbook captures the operating rules for deterministic, reproducible backtests in this repo.

## No Lookahead

- A prediction run may use only data on or before the cutoff date.
- Future prices are allowed only in the outcome evaluator after the signal has been recorded.
- Entry price, indicators, patterns, fundamentals, and agent scores must be computed from the cutoff-date view.
- CLI scripts should require an explicit `--date` or generated signal date rather than silently using latest data.

## Reproducibility

Each durable run should leave enough context to replay the result:

- Script name and git commit when available.
- Universe file/path and any sector filter.
- Signal dates, evaluation windows, and holding period.
- Agent settings or non-default thresholds.
- Data provider, cache policy, and API fallback behavior.
- Output paths for raw JSON/Excel/report artifacts.

Prefer a lightweight run manifest beside major outputs when a run is used for model comparison or public reporting.

## Universe Pinning

- Treat `data/halal_universe/halal_master.json`, `data/halal_universe/halal_sector_tickers.json`, and derived top-N files as explicit inputs.
- Record the exact universe file used by each backtest.
- Do not let a live screener mutate the tested universe during a historical run.
- If the universe is regenerated, keep the prior output or document the replacement.

## Metrics

Use the existing metric definitions and output-field guidance in `docs/BACKTEST_OUTPUT_FORMAT.md`.

Important concepts:

- Signal rows are keyed by ticker and cutoff date.
- Outcome fields use post-cutoff data only.
- `HIT_TARGET`, `HIT_STOP`, `EXPIRED`, `OPEN`, `SKIP`, and `ERROR` should keep their existing meanings.
- Precision, win rate, abstention, and coverage should name the denominator used.

## Cache And Network Policy

- Tests must not require network access.
- Backtests should prefer one bulk data pull per ticker/horizon when practical.
- If Polygon is configured, keep Polygon as the primary OHLCV provider for Phoenix/orchestrator backtests.
- Fallback providers must be visible in warnings or run metadata.
- Cache reads are acceptable for repeatability; cache writes should not change scoring semantics.
- When comparing runs, pin cache state or refresh policy so data revisions do not masquerade as strategy changes.

## Canonical CLI (avoid script sprawl)

- Point-in-time batches and Phoenix+Fundamental fusion: `scripts/run_trading.py analyze` (see `MODULE_MAP.md`).
- Long-form monthly or parallel sector engines stay in `scripts/backtests/` but should be **invoked via** `scripts/run_trading.py backtest --engine <alias> -- ...` so aliases stay centralized.

### Cadence (daily vs weekly vs monthly)

Registered backtest engines mostly use **monthly signal windows** aligned with `backtests/common.MONTHS`. Extending to **daily or weekly** signal grids is a methodology change: implement inside the shared engine or add parameters there — do not fork another year-titled runner unless the evaluation logic truly differs.

---

## Operator runbook — run this yourself (no AI required)

Use this when you want **signals or fused outputs** for a halal sector (e.g. first **100** names from that sector’s JSON list), or when you want a **full historical backtest** delegated to an existing engine.

### Before you start

1. **Repo root** — Run every command from `MyTradingSpace/` (or use absolute paths to `scripts/`).
2. **Environment** — Copy `.env.example` → `.env` if needed; set **Polygon** (`POLYGON_API_KEY`) for OHLCV-dependent agents; Fundamental runs may use **yfinance** or **FMP** per `--fund-data-source`.
3. **Cutoff date** — Always pass **`--date YYYY-MM-DD`** for analysis runs so you never accidentally lookahead.
4. **Universe file** — Halal lists live under `data/halal_universe/` (`halal_sector_tickers.json` is the **full** per-sector lists; `HALAL_SECTORS` in code is a short **top-10–style** subset unless you opt into **full**).

### A) One sector, ~100 tickers — point-in-time Phoenix + Fundamental (primary path)

Outputs one JSON per ticker with **`fusion`**, **`phoenix`**, **`fundamental`** — suitable for scanning buy/sell-style signals from **`fusion.final_signal`** and **`fusion.orchestrator_score`**.

```bash
cd /path/to/MyTradingSpace

python scripts/run_trading.py analyze \
  --date 2026-05-01 \
  --fusion phoenix-fa \
  --halal-universe full \
  --halal-sector "Energy" \
  --halal-limit 100 \
  --output-dir data/output/run_energy_100_20260501
```

- Replace **`Energy`** with any sector key that exists in `halal_sector_tickers.json` (must match spelling; sector names are case-insensitive).
- **`--halal-limit 100`** takes the **first 100 tickers in file order** for that sector (typically market-cap–oriented ordering from extraction). Omit `--halal-limit` to run **all** tickers in that sector (can be large).
- **`--halal-universe top10`** — only the short curated list (~10 names/sector); use when you want a quick smoke test without loading the full sector list.

**Reading results**

- Open `data/output/<your_run>/<TICKER>_<DATE>_phoenix_fund.json`.
- Decision fields: `fusion.final_signal` (`bullish` / `neutral` / `bearish`), `fusion.orchestrator_score`, `fusion.conflict_detected`.
- Raw agents: `phoenix.signal` (`BUY`/`WATCH`/`AVOID`), `fundamental.experimental_score`.

### B) Explicit ticker list (paste from Excel / your own screen)

```bash
python scripts/run_trading.py analyze \
  --date 2026-05-01 \
  --fusion phoenix-fa \
  --tickers "XOM,CVX,COP,SLB,VLO" \
  --output-dir data/output/custom_list
```

### C) Random N tickers across several sectors ( unbiased sample from union )

```bash
python scripts/run_trading.py analyze \
  --date 2026-05-01 \
  --fusion phoenix-fa \
  --halal-universe full \
  --halal-sectors "Energy,Consumer Staples" \
  --random-sample 50 \
  --seed 42 \
  --output-dir data/output/random_sample
```

### D) Historical monthly backtest (heavy engine — still one command surface)

Do **not** reimplement months/plumbing; delegate:

```bash
python scripts/run_trading.py backtest --engine halal-orchestrator-2025 -- \
  --sector "Energy" \
  --resume
```

Pass **`--help`** to the engine after `--` for engine-specific flags (`--months`, `--tickers`, etc.). Prefer **`--resume`** for long runs.

Other aliases (see `scripts/run_trading.py` → `BACKTEST_ENGINES`): `phoenix-fund-2025`, `phoenix-orchestrator-2025`, `orchestrator-legacy`, `sector-legacy`.

### F) Labeled Phoenix+FA window pilot — **single entry script** (tickers *or* sector)

**Canonical engine:** `halal-sector-pilot` → `scripts/backtests/run_halal_sector_month_pilot.py`.  
Do **not** fork another runner for the same job — pass universe + `--signal-date` only.

Runs **one** evaluation window per ticker: **`--signal-date`** (required) and **`--eval-days`** (default 30). Phoenix + Fundamental use **`as_of_date = signal_date` only**; forward Polygon prices are for outcome labeling only.

**Universe — choose exactly one:**

| Mode | Flags |
|------|--------|
| Explicit symbol(s) | `--tickers AMAT` or `--tickers AAPL,MSFT` |
| Halal sector slice | `--sector "Information Technology"` + `--limit N` (+ optional `--random-sample`) |

Writes **`run_bundle.json`**, `confusion_matrix.json`, `pilot_manifest.json`, `per_ticker/*.json` under **`--output-dir`** (default `data/output/trading_runs/phoenix_fa_window_pilot`). Dashboard: **`backtest-dashboard` → `/trading-runs`**.

**One ticker (e.g. Applied Materials):**

```bash
cd /path/to/MyTradingSpace

python scripts/run_trading.py backtest --engine halal-sector-pilot -- \
  --tickers AMAT \
  --signal-date 2025-09-01 \
  --workers 1 \
  --output-dir data/output/trading_runs/amat_2025-09-01
```

**Sector batch:**

```bash
python scripts/run_trading.py backtest --engine halal-sector-pilot -- \
  --sector "Information Technology" \
  --limit 50 \
  --signal-date 2024-12-31 \
  --workers 6 \
  --output-dir data/output/trading_runs/it_batch
```

Pass **`--random-sample`** with **`--sector`** to draw tickers uniformly (**`--seed`** for reproducibility).

### E) Legacy TA+FA orchestrator (same CLI)

```bash
python scripts/run_trading.py analyze \
  --date 2026-05-01 \
  --fusion ta-fa \
  --halal-universe full \
  --halal-sector "Energy" \
  --halal-limit 100 \
  --output-dir data/output/ta_fa_energy_100
```

Or use the shim: `python scripts/run_orchestrator_tickers.py ...` (defaults to **ta-fa**).

### Troubleshooting

| Symptom | Check |
|--------|--------|
| `Unknown halal sector` | Sector string must match keys in `halal_sector_tickers.json` (e.g. `Consumer Staples` not `Consumer_Staples`). |
| Rate limits / timeouts | Reduce `--halal-limit`, add resume-capable **backtest** engine with `--resume`, or run fewer tickers. |
| Different results tomorrow | Data revision / API — record **git commit**, **`--date`**, and **universe** (`--halal-universe`, sector) in a small manifest next to outputs. |

### Future: scheduled pre-market runs (not implemented)

When you ship automation, the same commands above map cleanly to a scheduler (cron, GitHub Actions, Kubernetes CronJob, etc.):

- **Trigger**: weekday **before RTH** (your timezone).
- **Wrapper**: shell script or Makefile target that `cd`’s to repo, activates venv, runs **`analyze`** or **`backtest`** with pinned `--date` (usually **previous trading day close**).
- **Artifacts**: sync `data/output/...` to object storage or attach reports; log stdout/stderr.
- **Secrets**: inject `.env` or secret manager for Polygon/FMP — never commit keys.

Until then, keep using this playbook manually; no extra scripts are required beyond `scripts/run_trading.py`.

---

## `run_bundle.json` — stable aggregate for UI & comparisons

Every `python scripts/run_trading.py analyze …` run (unless `--skip-bundle`) writes **`run_bundle.json`** next to the per-ticker JSON files in `--output-dir`.

### Schema guarantees

| Field | Purpose |
| --- | --- |
| `schema_version` | **`1.1.0`** today — bump only when adding optional fields or documenting breaking changes. UI should tolerate unknown keys. |
| `run_id` | `--run-label` or auto id — stable handle for logs. |
| `created_at_utc` | ISO timestamp of aggregation. |
| `as_of_date` | Shared cutoff for all rows. |
| `fusion` | `phoenix-fa`, `ta-fa`, `phoenix`, or `compare`. |
| `rows[]` | One object per ticker; includes `sector` when ticker appears in `halal_sector_tickers.json`. Phoenix modes include **`trade_levels`** (`entry_price`, `target_1`, `target_2`, `stop_price`, `exit_price` usually null, `pattern_name`, `pattern_breakout`). |
| `matrices` | **Signal alignment** counts (fusion vs Phoenix direction), not full TP/FP unless `evaluation.signal_correct` is filled by a future backtest merge. |

### Confusion-style matrices

- **`matrices.fusion_signal_counts`** — distribution of CWAF `fusion_final_signal`.
- **`matrices.phoenix_signal_counts`** — BUY / WATCH / AVOID counts.
- **`matrices.cross_tab_fusion_vs_phoenix_direction`** — 3×3 alignment (fusion rows × Phoenix mapped to bull/neutral/bear).
- **`matrices.confusion_when_labeled`** — TP/FP/TN/FN populate only when `rows[].evaluation.signal_correct` is set (e.g. after merging monthly backtest outcomes). Until then, use alignment tables for QA.

### Compare two runs (CLI)

Writes a **separate** delta file — UI and automation should prefer this for “yesterday vs today”:

```bash
python scripts/run_trading.py compare \
  --bundle-a data/output/trading_runs/run_a/run_bundle.json \
  --bundle-b data/output/trading_runs/run_b/run_bundle.json \
  --out data/output/trading_runs/deltas/a_vs_b.json
```

### Dashboard (Next.js)

From `backtest-dashboard/`:

```bash
npm run dev
```

Open **`/trading-runs`** — picks up every `data/output/trading_runs/**/run_bundle.json`, sector filter, matrix JSON, and optional **Compare with** second run for per-ticker delta. Same comparison logic exists in **`app/lib/compareRunBundles.ts`** (keep in sync with `scripts/lib/run_bundle.py` when changing deltas).

Legacy **`/phoenix-scans`** still reads older `phoenix_sector_scan_*.json` layouts.
