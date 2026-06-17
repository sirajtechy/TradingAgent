# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows semantic versioning where practical.

## [Unreleased]

_Nothing pending._

---

## [2026-06-17] — SEC EDGAR insider, Research Lab deep analyze, portfolio intelligence

Merged branch `feature/sec-edgar-insider-research-lab` into `main`. Major expansion beyond Phoenix+FA daily production: full intelligence fusion, dashboard deep-dive UI, SEC Form 4 insider sales, portfolio engine, and loop engineering scaffold.

### Added — SEC EDGAR insider agent

- **`agents/insider/edgar_client.py`** — Ticker → CIK → SEC submissions → Form 4 XML parsing.
- **Sale-only pipeline** — includes `nonDerivativeTransaction` rows where `transactionCode == "S"` and `securityTitle` contains **Common Stock**; skips missing/zero price rows.
- **Aggregation** — `total_shares_sold`, `total_dollar_sold`, `avg_sale_price`, **`per_insider_sales`** breakdown (owner, shares, dollars, avg price, sale count, **first/last sale dates**).
- **URL resolution** — `{cik}/{accClean}/{accClean}.xml` with fallback to raw `form4.xml` via filing index (XSL HTML paths excluded).
- **Dedup** — original + amended Form 4 filings collapsed to latest filing.
- **Config** — `INSIDER_DATA_SOURCE=auto|edgar|fmp|yfinance`; `SEC_EDGAR_USER_AGENT` required by SEC (see `.env.example`).
- **Tests** — `tests/test_insider_edgar.py`.

### Added — Research Lab deep analyze

- **Dashboard routes**
  - `/research/analyze` — single-ticker fusion dashboard with agent sidebar + detail panels.
  - `/research/analyze/watchlist` — batch deep dive for all Phoenix **BUY/WATCH** names from `master_pilot.json`.
- **API** — `apps/backtest-dashboard/app/api/analyze/` and `.../watchlist/`.
- **Shared UI** — `apps/backtest-dashboard/app/research/analyze/analyzeUi.tsx` (fusion hero, agent grid, insider sale table, headlines, source tier badges).
- **CLI / pipeline**
  - `./bin/mts analyze --fusion full --export-breakdown --refresh-context`
  - `./bin/mts analyze --watchlist --fusion full --max-tickers N --force`
  - `pipelines/watchlist.py`, JSON auto-save to `data/output/research/<date>/`.
- **Agent breakdown** — `agents/orchestrator/agent_breakdown.py`: one-liners, insights, headlines (top 10), `source_tier`, data legitimacy map.

### Added — Intelligence agents & data layer

- **Macro** — FRED primary (`FRED_API_KEY`); yfinance fallback for rates/CPI.
- **Market summary** — Polygon SPY/sectors + hybrid yfinance VIX when Polygon `I:VIX` returns 403.
- **News** — FMP → optional **Finnhub** (`agents/news/finnhub_client.py`) → yfinance; richer bullets and headline export.
- **Geopolitics** — FMP scan with improved yfinance context headlines when geo keywords miss.
- **Sentiment** — labeled **Derived** in dashboard (composite of upstream agents, not a standalone API).
- **Session context cache** — `data/output/context/context_<date>.json`; `--refresh-context` bypasses stale cache after key changes.
- **Config schema** — `core/config_schema.py`; `./bin/mts config validate`.
- **Docs** — `docs/specs/INTELLIGENCE_DATA_PLAN.md`, updates to `docs/specs/FREE_DATA_SOURCES.md`.

### Added — Portfolio intelligence engine

- **`agents/portfolio/`** — momentum scorer, selector, sizer, FRR rebalancer, regime guard, simulator, enrich, sector report.
- **CLI** — `./bin/mts portfolio backtest`, `./bin/mts portfolio allocate` with `--full-agents`, `--strategy-profile blend`.
- **Dashboard** — `/research/portfolio`.
- **Config** — `data/config/portfolio_rules.json`.
- **Docs** — `docs/specs/PORTFOLIO_ENGINE.md`, `docs/MYTRADINGSPACE_ONE_PAGER.md`.
- **Tests** — `tests/test_portfolio.py`.

### Added — Trader strategy profiles

- **`agents/strategies/`** — Minervini, Moglen, Breitstein, McIntosh modules + `blend` fusion.
- **CLI** — `./bin/mts strategy --ticker X --profile minervini|blend|...`
- **Analyze integration** — `--strategy-profile blend` on `./bin/mts analyze`.
- **Tests** — `tests/test_strategies.py`.

### Added — Loop engineering scaffold

- **`.loop/`** — roadmap, policies, skills, state, agent prompts.
- **`scripts/loop_*.py`** — triage, plan, verify, ops, worktree spawn.
- **GitHub workflows** — loop triage, feature build, review gate, ops daily.
- **`AGENTS.md`**, `skills/tradingagent-loop-engineering-scaffold.md`.
- **Tests** — `tests/test_loop_engine.py`.

### Changed

- **`agents/insider/composite_client.py`** — auto mode prefers EDGAR → FMP → yfinance.
- **`agents/insider/rules.py`** — sale-focused metrics, per-insider aggregation, data quality downgrade on dedup warnings.
- **`agents/orchestrator/pipeline_full.py`** — full fusion runs all intelligence agents; human decision mode preserved.
- **`pipelines/analyze.py`** — `.env` loading, JSON export paths, watchlist batch, context refresh flag.
- **`cli/__main__.py`** — analyze watchlist, portfolio, strategy, agent, context, loop, config validate commands.
- **`apps/backtest-dashboard/app/research/layout.tsx`** — nav links for Analyze and Portfolio.
- **README.md** — expanded for all new surfaces (this release).

### Fixed

- **Insider value aggregation** — derivative Form 4 rows no longer multiply total-dollar fields by share count (eliminated trillion-dollar totals on names like CRWV).
- **Form 4 XML parsing** — nested `<value>` elements and raw XML URL resolution (XSL HTML no longer parsed as trades).
- **Macro cache** — stale `context_<date>.json` could show yfinance rates after FRED key added; use `--refresh-context`.
- **`agent_breakdown.py`** — insider block indentation restored inside agent loop.

---

## [Earlier — pre-2026-06-17 backlog]

Items below were tracked under `[Unreleased]` before the 2026-06-17 release.

### Added

- **`halal-sector-pilot`** backtest engine (`scripts/backtests/run_halal_sector_month_pilot.py`): halal sector slice, single-window Phoenix+FA labeled run with **`run_bundle.json`** for `/trading-runs`, **`confusion_matrix.json`**, and explicit **`no_lookahead_statement`** in `pilot_manifest.json`.
- **`trade_levels`** on Phoenix `analyze_ticker` output (`entry_price`, `target_1`, `target_2`, `stop_price`, `exit_price` always present with `exit_price` null until execution/backtest merge; `pattern_name` / `pattern_breakout` for the structural pattern snapshot).
- **`run_bundle.json` schema 1.1.0**: each `phoenix-fa` and `phoenix` row includes **`trade_levels`** (mirrors Phoenix when available).
- **`OrchestratorSettings.phoenix_fund_weights`**: default **90% / 10%** Phoenix vs Fundamental for `fuse_signals_phoenix` (separate from TA+FA `weights`).

- Canonical CLI `scripts/run_trading.py`: `analyze` (default fusion **phoenix-fa** = Phoenix + Fundamental CWAF; also `ta-fa`, `phoenix`, `compare`) and `backtest --engine` delegates to registered long-form runners without duplicating logic.
- `--halal-universe full` on `run_trading.py analyze` loads full sector lists from `halal_sector_tickers.json` (with `--halal-limit N` for e.g. 100 tickers); `top10` keeps the short curated list.
- **`run_bundle.json`** aggregate (`schema_version` 1.1.0) + signal alignment matrices after each `analyze`; **`run_trading.py compare`** emits delta JSON for run-vs-run QA.
- **Backtest dashboard** `/trading-runs` lists bundles under `data/output/trading_runs/`, sector filter, matrix preview, and compare-with-run deltas (`app/lib/compareRunBundles.ts`).
- Added refactor guardrails, backtest playbook, Phoenix contract spec, orchestrator mode guide, multi-agent contract, and module map documentation.
- Added synthetic Phoenix tests for hard filters and pattern dispatch.
- Added orchestrator `FusionMode` + `fuse_by_mode` dispatcher (`agents/orchestrator/modes.py`) for TA+FA vs Phoenix+FA fusion.
- Added `agent_envelope` helpers mapping native TA / FA / Phoenix dicts into the multi-agent contract envelope (`agents/orchestrator/agent_envelope.py`).
- Added tests: `tests/orchestrator/test_modes_and_envelope.py`, `tests/phoenix/test_scoring.py`.

### Changed

- **`halal-sector-pilot`** (`run_halal_sector_month_pilot.py`): universe is **either** `--tickers` **or** `--sector` (required XOR); **`--signal-date` is required**; generic default **`--output-dir`**. Prefer this single script instead of duplicating pilot runners.
- **`fuse_signals_phoenix`** blends Phoenix + FA using **`phoenix_fund_weights`** (default **90% / 10%**) instead of the TA+FA `weights` table.
- Split Phoenix pattern detection into focused detector modules while preserving the `agents.phoenix.patterns.detect_all_patterns` public import path.
- `scripts/run_orchestrator_tickers.py` is now a compatibility shim that forwards to `run_trading.py analyze` (defaults `--fusion ta-fa` when omitted; maps legacy `--strategy`).

## [2026-05-11]

Dated integration branch: **Phoenix + halal sector pilot outputs**, **trading-run bundles** in the **Next.js backtest dashboard**, and supporting **orchestrator / Phoenix refactors** and **tests**.

### Added — Dashboard (`backtest-dashboard`)

- **`/phoenix-watch-buy`**: sector **`master_pilot.json`** loaded via **`/api/trading-runs/bundle`** (`rel` query); **All tickers** vs **BUY+WATCH** view; columns for **TP / FP / TN / FN** (signal vs label), **Category**, confusion counts; **sortable headers** on listed columns (sort resets when the selected run changes); **Excel export** uses the **current table sort order** and records **`view_all_tickers`** (and related meta) in the export sheet.
- **`app/lib/confusionBucket.ts`**: shared **`confusionBucket`** / **`confusionCells`** helpers for consistent confusion labels and sorting (reused from **`/trading-runs`**).
- **`/trading-runs`**: bundle listing and compare UX; **TP / FP / TN / FN** and **Category** for bundle rows when **`evaluation.signal_correct`** (and related fields) are present; run picker prefers **`kind === "bundle"`** for compare; API surfaces **`master_pilot.json`** as **`kind: "master"`** for master-sector summaries.
- **`app/api/trading-runs/`** route handlers (list, bundle, compare as implemented in-tree).
- **`app/lib/compareRunBundles.ts`**: helpers to diff / align **`run_bundle.json`** payloads for QA.

### Added — Pilot scripts, CLI, and sample outputs

- **`scripts/backtests/run_halal_sector_month_pilot.py`**: halal **sector** (or explicit tickers), **`--signal-date`**, **`--single-master-json`** / **`master_pilot.json`** aggregate with per-ticker trading + confusion-style fields for dashboard consumption.
- **`scripts/run_trading.py`** and **`scripts/lib/`**: canonical analyze / backtest / compare entry paths; supporting utilities.
- **`requirements-backtest.txt`**: pinned or grouped deps for long-form backtest runs.
- Additional one-off / study runners under **`scripts/backtests/`** (e.g. Phoenix + orchestrator / polygon study scripts) and **`run_until_done.sh`** where present.
- **`data/output/trading_runs/`**: checked-in (or generated-then-committed) **sector `master_pilot.json`** and related bundle artifacts used to validate **`/trading-runs`** and **`/phoenix-watch-buy`**.

### Added — Agents, fusion, and contracts

- **`agents/phoenix/patterns/`**: split pattern detectors from the former monolithic **`agents/phoenix/patterns.py`** (removed) while keeping a stable **`agents.phoenix.patterns.detect_all_patterns`** import path; **`agents/phoenix/pattern_helpers.py`** and **`agents/phoenix/service.py`** updates accordingly.
- **`agents/orchestrator/modes.py`**, **`fusion_phoenix.py`**, **`backtest_phoenix.py`**, **`agent_envelope.py`**: Phoenix + FA fusion modes, backtest hooks, and envelope mapping into the multi-agent contract.
- **`OrchestratorSettings.phoenix_fund_weights`** and **`fuse_signals_phoenix`** behavior (see **[Unreleased]**): default **90% / 10%** Phoenix vs Fundamental, separate from TA+FA weights.

### Added — Tests

- **`tests/phoenix/`**: synthetic tests for scoring / filters / pattern dispatch surfaces.
- **`tests/orchestrator/`** (e.g. modes + envelope), **`tests/test_fusion_phoenix.py`**, **`tests/test_run_bundle.py`**: fusion and bundle JSON invariants.
- Updates to **`tests/test_orchestrator_graph.py`**, **`tests/test_technical_indicators.py`**, **`tests/test_technical_rules.py`** for orchestrator and indicator behavior.

### Added — Documentation and repo hygiene

- **`docs/BACKTEST_PLAYBOOK.md`**, **`docs/MULTI_AGENT_CONTRACT.md`**, **`docs/REFACTOR_GUARDRAILS.md`**, **`MODULE_MAP.md`**, **`ORCHESTRATOR_MODES.md`**, **`PHOENIX_AGENT_SPEC.md`**; updates to **`docs/PHOENIX_AGENT_IMPLEMENTATION.md`**.
- Root **`CHANGELOG.md`** (this file) and **`MODULE_MAP.md`** for traceability across agents and dashboard.

### Changed

- **`backtest-dashboard/app/page.tsx`**, **`phoenix-scans/page.tsx`**, and refreshed **`app/data/dashboard-data.json`** for navigation / scan summaries aligned with new routes.
- **`agents/orchestrator/config.py`**, **`fusion.py`**, **`agents/polygon_data/__init__.py`**, **`agents/technical/indicators.py`**, **`scripts/run_halal_predictions.py`**: wiring and indicator/orchestrator tweaks supporting the above.
- **`scripts/run_orchestrator_tickers.py`**: shim forwarding to **`run_trading.py analyze`** (legacy flags mapped; default fusion **`ta-fa`** when omitted).

### Fixed

- **`/phoenix-watch-buy`**: table sort for **`tp` / `fp` / `tn` / `fn`** columns maps through **`confusionCells`** / **`CONFUSION_MARK_KEY`** so header sort matches stored evaluation keys (avoids silent wrong-key sorts).
