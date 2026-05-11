# MyTradingSpace — Multi-Agent Stock Analysis Platform

A **deterministic, rule-based** multi-agent stack for point-in-time stock analysis, halal-universe screening, Phoenix-style pattern scoring, and **Confidence-Weighted Asymmetric Fusion (CWAF)** across agents. Outputs feed **JSON run bundles**, **backtests**, and a **Next.js backtest dashboard**. No LLM influences numeric scores or pass/fail gates.

---

## What This Repository Does

For a **ticker**, **as-of date**, and optional **holding window**, the system can:

1. Run the **Fundamental** agent (FMP-backed frameworks) for financial health, valuation, quality, and growth.
2. Run the **Technical** agent (Polygon OHLCV) across momentum, trend, and pattern-style rule sets.
3. Run the **Phoenix** agent for stage/pattern/risk scoring and trade-level hints used in Phoenix-only or fused flows.
4. **Fuse** agents through the **Orchestrator** — e.g. **TA+FA** (`fuse_signals`) or **Phoenix+FA** (`fuse_signals_phoenix` / `FusionMode.PHOENIX_FUND`, default **90% / 10%** Phoenix vs fundamental weights).
5. Emit structured **BUY / SELL / HOLD** (and related) recommendations, **run_bundle.json** aggregates, confusion-style evaluation when labels exist, and exports for Excel/JSON and the dashboard.

Canonical entry points and module boundaries are summarized in **`MODULE_MAP.md`** (start there when navigating or extending the codebase).

---

## Top-Level Layout

```
MyTradingSpace/
├── agents/                    # Bounded agent packages (import from agents.*)
│   ├── fundamental/           # FMP-based fundamental scoring + graph/service
│   ├── technical/             # Polygon TA rules, indicators, predictor, graph
│   ├── phoenix/               # Phoenix agent: scoring, filters, stage, reporting
│   │   ├── patterns/          # Split pattern detectors (VCP, pullback, flag, …)
│   │   └── pattern_helpers.py
│   ├── orchestrator/          # Fusion, LangGraph-style graph, CWAF, Phoenix fusion
│   │   ├── fusion.py          # TA+FA fusion
│   │   ├── fusion_phoenix.py  # Phoenix+FA fusion
│   │   ├── modes.py           # FusionMode dispatcher (ta-fa vs phoenix-fa, …)
│   │   ├── agent_envelope.py  # Normalized multi-agent envelopes
│   │   ├── graph.py / service.py / backtest*.py
│   │   └── config.py          # OrchestratorSettings (incl. phoenix_fund_weights)
│   ├── polygon_data/          # Shared Polygon OHLCV access
│   ├── oneil/                 # O’Neil-style stage / breakout helpers
│   └── prediction/            # Strategy formatting / backtester utilities
├── backtests/                 # Long-form Python backtest drivers (per engine)
├── backtest-dashboard/        # Next.js (App Router) UI + API routes → see its README
├── scripts/
│   ├── run_trading.py         # **Canonical CLI**: analyze | backtest | compare
│   ├── lib/                   # Shared helpers (e.g. run_bundle aggregation)
│   ├── backtests/             # Thin runners / pilots (halal sector month, …)
│   ├── run_halal_predictions.py
│   ├── run_orchestrator_tickers.py   # Shim → run_trading.py analyze (legacy flags)
│   └── analysis/ | dashboard/ | polygon/ | workstreams/   # Ad-hoc pipelines
├── tests/                     # Pytest suite
│   ├── phoenix/               # Phoenix unit / synthetic tests
│   └── orchestrator/          # Modes + envelope tests
├── data/
│   ├── input/                 # Universe files, caches, master dumps
│   ├── halal_universe/        # Halal lists / loaders
│   └── output/                # Generated artifacts (see .gitignore for some trees)
│       ├── trading_runs/      # run_bundle.json, master_pilot.json, pilots
│       ├── orchestrator_runs/ # Sample per-ticker JSON (when committed)
│       ├── predictions/       # Ignored: generated predictions
│       └── backtests/         # Ignored: heavy backtest exports
├── docs/                      # Playbooks, contracts, implementation notes
├── prompts/                   # Agent steering / prompt assets
├── agent_learning/            # Human-written steering per agent area
├── trading-strategies/        # Strategy notes / configs (as used in-repo)
├── CHANGELOG.md               # Keep a Changelog–style history
├── MODULE_MAP.md              # Feature → spec → module → tests → scripts
└── ORCHESTRATOR_MODES.md      # Fusion modes and CLI guidance
```

---

## Modularity (How Pieces Fit)

| Layer | Role |
| --- | --- |
| **`agents/*`** | Each agent owns its **data clients**, **rules/scoring**, **graph** (where applicable), and **reporting**. Keep new logic inside the right package; expose narrow public APIs. |
| **`agents/orchestrator`** | **Single place** for combining agent outputs: TA+FA and Phoenix+FA paths, **modes**, **envelopes**, and **backtest** glue. Prefer extending `modes.py` / fusion modules over duplicating fusion in scripts. |
| **`scripts/run_trading.py`** | **Preferred CLI** for `analyze`, `backtest --engine <alias>`, and `compare`. New batch behavior should extend flags or registered engines, not fork one-off CLIs (see `MODULE_MAP.md`). |
| **`scripts/lib/`** | Non–agent-specific building blocks (bundle JSON, shared pilot helpers) used by CLI and backtests. |
| **`backtest-dashboard/`** | Read-only visualization over committed or mounted JSON under `data/output/`; API routes under `app/api/` proxy the filesystem for local QA. |
| **`tests/`** | Mirrors critical packages (`phoenix/`, `orchestrator/`) plus integration-style tests at repo root. |

---

## Documentation Map

| Document | Contents |
| --- | --- |
| `MODULE_MAP.md` | Feature areas, specs, modules, tests, and scripts in one table |
| `ORCHESTRATOR_MODES.md` | `FusionMode`, `phoenix-fa` vs `ta-fa`, weights |
| `docs/BACKTEST_PLAYBOOK.md` | Engines, outputs, `run_bundle` usage |
| `docs/MULTI_AGENT_CONTRACT.md` | How future agents plug into the same envelope pattern |
| `docs/PHOENIX_AGENT_IMPLEMENTATION.md` | Phoenix implementation detail |
| `CHANGELOG.md` | Notable changes (including dated integration notes) |

---

## Key Scripts (Current)

| Path | Purpose |
| --- | --- |
| **`python scripts/run_trading.py analyze`** | Point-in-time analysis: `--fusion phoenix-fa` (default Phoenix+FA), `ta-fa`, `phoenix`, `compare`; halal flags (`--halal-universe`, `--halal-sector`, …) per `MODULE_MAP.md` |
| **`python scripts/run_trading.py backtest --engine …`** | Delegates to registered long-form backtest engines |
| **`python scripts/run_trading.py compare`** | Run-vs-run deltas for QA |
| **`scripts/backtests/run_halal_sector_month_pilot.py`** | Sector (or ticker list) pilot: **`--signal-date`**, optional **`--single-master-json`** / `master_pilot.json` for dashboard bundles |
| **`scripts/run_halal_predictions.py`** | Batch halal predictions (Excel + JSON) |
| **`scripts/run_orchestrator_tickers.py`** | **Shim** to `run_trading.py analyze` (legacy entry; defaults TA+FA if fusion omitted) |
| **`backtests/run_*.py`** | Standalone engine drivers where still used |

Heavy generated trees under `data/output/predictions/` and `data/output/backtests/` are **gitignored**; **`data/output/trading_runs/`** may contain committed sample bundles for the dashboard (see repo state).

---

## Backtest Dashboard (`backtest-dashboard/`)

Next.js **App Router** app. Main **routes**:

| Route | Purpose |
| --- | --- |
| `/` | Home / navigation hub |
| `/halal` | Halal prediction views |
| `/sectors` | Sector-oriented views |
| `/phoenix-scans` | Phoenix scan listings and drill-down |
| **`/trading-runs`** | Lists `data/output/trading_runs/**`; bundle compare, confusion columns when evaluations exist |
| **`/phoenix-watch-buy`** | Sector **`master_pilot.json`** via **`/api/trading-runs/bundle`**; BUY+WATCH vs all tickers; sortable table + Excel export |

**API (selected):** `app/api/trading-runs/`, `app/api/phoenix-scans/`, `app/api/halal-predictions/`, `app/api/sectors-predictions/`.

```bash
cd backtest-dashboard
npm install
npm run dev          # default dev port 3000
# production
npm run build && npm run start   # set PORT=3055 (or any) as needed
```

See **`backtest-dashboard/README.md`** for dashboard-focused setup.

---

## Environment Setup

```bash
# Python: use a project venv at repo root or your preferred path
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional: long / pinned backtest stacks
pip install -r requirements-backtest.txt

# API keys (Fundamental + Polygon)
export FMP_API_KEY=your_fmp_key
export POLYGON_API_KEY=your_polygon_key
```

---

## Running Tests

```bash
python -m pytest -q
# Targeted:
python -m pytest -q tests/phoenix tests/orchestrator
```

---

## The Three “Classic” Agents (Plus Phoenix)

The original README tables for **Fundamental (v3)** and **Technical (v2)** framework weights still apply conceptually; orchestrator headline metrics were historically quoted for **TA+FA CWAF**. **Phoenix** adds a separate scoring path and **Phoenix+FA** fusion — see `ORCHESTRATOR_MODES.md` and Phoenix docs for weights and behavior.

---

## Important Limitations

- Scores and labels are **research / backtest oriented**, not a guarantee of live performance.
- Shariah screening uses pragmatic proxies (e.g. interest income ratio); not a full fiqh board–grade classification.
- Point-in-time constraints: some metadata (e.g. sector/industry) may come from endpoints without full historical snapshots; estimates may be excluded where documented.
- Dashboard APIs read local JSON; secure or authenticate before exposing beyond localhost.

---

## License / Contact

Project-specific license and maintainer notes live with the upstream **`TradingAgent`** repository settings on GitHub.
