# App improvement — MyTradingSpace refactor

Documentation for the planned refactor of **MyTradingSpace**, **AI-space/TradingAgent**, and related tooling into an isolated, skill-driven, multi-agent architecture.

**Status:** In progress (Phase 1–3 landed with shims)  
**Last updated:** 2026-05-23

---

## Goals

| Goal | Description |
|------|-------------|
| **Isolation** | One folder per agent; no cross-agent imports except via orchestrator + envelopes |
| **Readability** | Utility-based `core/` package; thin CLIs and pipelines |
| **Scalability** | Parallel sector pilots, registry-based fusion, pluggable future agents |
| **Agnostic scripts** | Scripts call `pipelines/` or `run_trading.py` — never duplicate fusion logic |
| **Agent interaction** | Agents communicate via `AgentEnvelope` (`docs/MULTI_AGENT_CONTRACT.md`) |
| **Skills alignment** | Trading-specific skills in `AI-space/TradingAgent/skills/`; engineering workflow from `AI-space/AI-Brain/agent-skills/` |

---

## Production paths to preserve

These must keep working throughout the refactor (parity tests):

```bash
# Point-in-time analysis (default production fusion)
python scripts/run_trading.py analyze --fusion phoenix-fa --ticker AAPL --date YYYY-MM-DD

# All-sector unified pilot
python scripts/backtests/run_master_data_parallel_pilot.py \
  --signal-date YYYY-MM-DD --merged-output data/output/trading_runs/unified_master_<date>/master_pilot.json

# OpenClaw / phone
openclaw/scripts/orchestrator_analyze.sh --ticker AAPL --date YYYY-MM-DD --fusion phoenix-fa
```

**Do not** use `agents/orchestrator/service.py` for Phoenix workflows — that path is **TA+FA LangGraph only**.

---

## Current state (summary)

| Area | Location | Issue |
|------|----------|--------|
| Agents | `MyTradingSpace/agents/*` | Circular imports (technical ↔ orchestrator); orchestrator knows all internals |
| Scripts | `scripts/`, `scripts/backtests/`, `backtests/` | 40+ scripts; many bypass `run_trading.py`; duplicate backtest trees |
| Polygon | `agents/polygon_data/`, `scripts/polygon/` | Two clients |
| OpenClaw | `openclaw/scripts/` | Re-implements fusion branching from `run_trading.py` |
| Dashboard | `backtest-dashboard/` | Reads `data/output/trading_runs/`; export logic scattered |
| TradingAgent specs | `AI-space/TradingAgent/prompts/prompts.md` | Backlog only; no formal specs folder |
| Skills | OpenClaw + AI-Brain | Not aligned with repo layout |

---

## Target architecture

```
Siraj-Hustle/
├── App-improvement/                 # This folder — plans, ADRs, progress
├── AI-space/
│   ├── TradingAgent/
│   │   ├── specs/                   # Contracts, fusion rules, ADRs
│   │   ├── skills/                  # Trading Cursor/OpenClaw skills
│   │   ├── prompts/
│   │   └── backlog/
│   └── AI-Brain/agent-skills/       # Generic engineering skills (unchanged)
│
└── MyTradingSpace/
    ├── core/                        # Shared utilities (agent-agnostic)
    │   ├── contracts/               # AgentEnvelope, MasterPilot schemas
    │   ├── data/                    # Single Polygon client
    │   └── io/                      # Bundle merge, confusion, export
    ├── agents/                      # One bounded agent per folder
    │   ├── phoenix/
    │   ├── fundamental/
    │   ├── technical/
    │   ├── orchestrator/            # Fusion hub + registry only
    │   └── _registry.py
    ├── pipelines/                   # Agnostic workflows (no LLM)
    │   ├── analyze.py
    │   ├── sector_pilot.py
    │   ├── unified_pilot.py
    │   └── daily.py
    ├── cli/
    │   └── run_trading.py           # Thin CLI → pipelines
    ├── apps/
    │   ├── backtest-dashboard/
    │   └── openclaw/                # Thin wrappers only
    └── data/
```

**Interaction model:** CLI/OpenClaw → orchestrator → agent registry → `analyze()` → envelope → `fuse_by_mode` → `MasterPilot` / `RunBundle` → dashboard.

---

## Implementation phases

### Phase 0 — Spec & contract (1–2 days)

**Skills:** `spec-driven-development`, `documentation-and-adrs`

- Promote `AI-space/TradingAgent/` to spec home (contracts, MODULE_MAP, fusion docs).
- Convert `prompts/prompts.md` backlog into tracked spec items.
- Define JSON schemas in `core/contracts/`: `AgentEnvelope`, `MasterPilot`, `RunBundle`.
- **ADR-001:** Scripts call pipelines, not agent internals.

**Deliverable:** Spec folder + ADRs; no behavior change.

---

### Phase 1 — Core utilities (2–3 days)

**Skills:** `incremental-implementation`, `api-and-interface-design`

Extract into `core/`:

| Module | Source | Purpose |
|--------|--------|---------|
| `core/data/polygon.py` | `agents/polygon_data` + `scripts/polygon/` | Single Polygon client |
| `core/io/master_pilot.py` | Pilot merge/confusion logic | Sector merge, confusion matrix |
| `core/io/run_bundle.py` | `scripts/lib/run_bundle.py` | Dashboard artifacts |
| `core/universe/` | Halal + master_data loaders | Ticker/sector resolution |
| `core/paths.py` | Existing `paths.py` | Repo paths |

**Deliverable:** Core package + tests; compatibility shims for agents.

---

### Phase 2 — Agent isolation (3–5 days)

**Skills:** `code-simplification`, `test-driven-development`

Per-agent layout:

```
agents/<name>/
├── __init__.py      # public: analyze(ticker, as_of_date)
├── adapter.py       # native → AgentEnvelope
├── service.py
├── backtest.py      # optional
└── tests/
```

- Break technical ↔ orchestrator circular import.
- Orchestrator registry: load agents via registry, fuse envelopes only.
- Export only `analyze()` + `adapter.to_envelope()`.

**Deliverable:** Isolated agents; orchestrator integration tests green.

---

### Phase 3 — Agnostic pipelines (3–4 days)

**Skills:** `deprecation-and-migration`, `performance-optimization`

| Pipeline | Replaces |
|----------|----------|
| `pipelines/analyze.py` | `run_trading.py analyze`, `orchestrator_analyze.py` |
| `pipelines/sector_pilot.py` | `run_halal_sector_month_pilot.py` |
| `pipelines/unified_pilot.py` | `run_master_data_parallel_pilot.py` |
| `pipelines/daily.py` | `run_daily_pipeline.sh` |

- Deprecate duplicate `backtests/` tree and monolithic scripts.
- OpenClaw skills call pipelines only — no duplicated fusion logic.

**Deliverable:** One canonical path per workflow.

---

### Phase 4 — TradingAgent skills (2–3 days)

**Skills:** `using-agent-skills`, `context-engineering`

Trading skills under `AI-space/TradingAgent/skills/`:

| Skill | Use case |
|-------|----------|
| `trading-analyze` | Single ticker phoenix-fa |
| `trading-sector-pilot` | One sector backtest |
| `trading-unified-pilot` | All sectors |
| `trading-dashboard` | Export / open UI |

Mirror (or symlink) into `openclaw/workspace/skills/`.

**Deliverable:** Shared skills for Cursor + OpenClaw + WhatsApp.

---

### Phase 5 — Dashboard & backlog (2–4 days)

**Skills:** `frontend-ui-engineering`, `debugging-and-error-recovery`

From `AI-space/TradingAgent/prompts/prompts.md`:

1. Fix missing Jan–Mar forecast / eval labels in 2025 JSON exports.
2. Reduce dashboard misclassifications — single preprocessing in `core/io`.
3. Dashboard remains read-only; business logic in pipelines/core.

**Deliverable:** Backlog items closed or spec’d with tests.

---

### Phase 6 — Scale & CI (ongoing)

**Skills:** `performance-optimization`, `ci-cd-and-automation`

- Configurable parallelism (`sector_jobs`, `workers`).
- CI: `pytest` on `core/`, `agents/`, `pipelines/` + smoke analyze.
- Optional: `--sectors Energy` on unified pilot (sector-only without full universe).

---

## PR sequence (recommended)

| PR | Scope |
|----|--------|
| PR1 | `core/contracts` + `core/io` extract |
| PR2 | Agent adapters + registry; fix circular imports |
| PR3 | `pipelines/analyze` + slim `run_trading.py` |
| PR4 | `pipelines/sector_pilot` + `unified_pilot`; deprecate duplicate backtests |
| PR5 | TradingAgent specs/skills + OpenClaw alignment |
| PR6 | Dashboard preprocessing + backlog fixes |

**Branch:** `refactor/agent-isolation-v1` (off current feature branch).

---

## Migration rules

1. **No big-bang** — shims keep old import paths until parity tests pass.
2. **Parity tests** — same ticker/date/fusion before vs after.
3. **Deprecate in layers** — scripts → pipelines → delete.
4. **External tools unchanged** — e.g. `external-tools/buy-signal-live-enrich/` stays outside agents.

---

## Open decisions

| # | Question | Options |
|---|----------|---------|
| 1 | Repo layout | Refactor in place under `MyTradingSpace/` vs new runtime root next to `AI-space/TradingAgent` |
| 2 | Scope | Full 6 phases vs MVP (Phases 0–3 only) |
| 3 | Legacy | Archive `run_halal_orchestrator_backtest_2025.py` (~1700 lines) after parity vs keep until 2025 replay proven |

---

## Related docs

| Path | Purpose |
|------|---------|
| `MyTradingSpace/MODULE_MAP.md` | Feature → module map |
| `MyTradingSpace/docs/MULTI_AGENT_CONTRACT.md` | Agent envelope contract |
| `MyTradingSpace/docs/BACKTEST_PLAYBOOK.md` | Backtest workflows |
| `MyTradingSpace/openclaw/README.md` | Phone/WhatsApp automation |
| `AI-space/AI-Brain/agent-skills/` | Generic engineering skills |
| `AI-space/TradingAgent/prompts/prompts.md` | Product backlog |

---

## Progress log

| Date | Phase | Notes |
|------|-------|-------|
| 2026-05-20 | — | Plan documented in `App-improvement/` |
| 2026-05-23 | 1–3 | `core/`, `pipelines/`, `agents/_registry.py`, specs; OpenClaw delegates to pipelines; sector-pilot skill |
| 2026-05-23 | cleanup | Specs → `docs/specs/`; stale scripts → `archive/`; `backtests/` trimmed to `common.py`; old runs → `data/archive/` |
| 2026-05-30 | plan | `PRODUCTION_PLAN.md` — `bin/mts` command surface, apps/ layout, dashboard Research Lab |
| 2026-05-30 | 1 | **`bin/mts` + `cli/`** — dashboard, sector, unified, lab, stop, export |
| 2026-05-30 | 2 | **`core/io/export.py`**, `/research/signals`, reconciled BUY+WATCH dump |
| 2026-05-30 | 3 | **`apps/`** — moved `backtest-dashboard/` + `openclaw/`; symlinks at old paths |
| 2026-05-30 | 4 | **Research Lab** — shared layout, pages under `/research/*`, redirects |
| 2026-05-30 | 5 | **Engine shrink** — `core/universe/`, polygon re-export, archived 6 legacy scripts |
