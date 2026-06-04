# Refactor plan — detailed reference

**Status:** Phase 1–3 implemented (shims); Phases 4–6 pending  
**Companion:** [README.md](./README.md)

---

## 1. Problem statement

MyTradingSpace grew organically: multiple backtest entry points, scripts that import agent internals directly, duplicated Polygon clients, and OpenClaw wrappers that re-implement CLI fusion logic. Adding agents (insider, macro, news) or running from phone/WhatsApp increases drift risk.

The refactor applies **separation of concerns**:

- **Agents** = analyze one domain, return native output + envelope adapter.
- **Orchestrator** = fuse envelopes only; no Phoenix/FA business logic inside fusion.
- **Pipelines** = batch workflows (sector pilot, unified pilot, daily) with no LLM.
- **CLI / OpenClaw** = thin entry; no duplicated branching.
- **Core** = shared data, IO, contracts, universe loaders.
- **Apps** = dashboard and OpenClaw consume artifacts; no scoring logic.

---

## 2. Agent envelope (interaction contract)

All agents normalize to the envelope in `MyTradingSpace/docs/MULTI_AGENT_CONTRACT.md`:

```json
{
  "agent_id": "phoenix",
  "as_of_date": "2026-05-20",
  "signal": "bullish",
  "score": 68.0,
  "confidence": "medium",
  "band": "good",
  "abstain": false,
  "reason": null,
  "data_quality": "good",
  "warnings": [],
  "extras": {}
}
```

Reference: `agents/orchestrator/agent_envelope.py`, `agents/orchestrator/modes.py` (`fuse_by_mode`).

Future agents (insider, macro, news) add `agents/<id>/` + `adapter.py` + registry entry — no changes to Phoenix/FA internals.

---

## 3. Coupling to remove

| Issue | Current | Target |
|-------|---------|--------|
| Dual backtest trees | `backtests/` + `scripts/backtests/` | Single `pipelines/` |
| Monolithic script | `run_halal_orchestrator_backtest_2025.py` (~1700 LOC) | Pipeline config + shared `_run_period` |
| OpenClaw duplication | `orchestrator_analyze.py` fusion branches | Call `pipelines/analyze` |
| Circular import | `technical/service` → `orchestrator/service` | Prediction bridge or orchestrator-only call |
| Dual Polygon | `polygon_data/` + `scripts/polygon/` | `core/data/polygon.py` |
| Export sprawl | 4+ dashboard export scripts | `core/io/export.py` |
| Shim default mismatch | `run_orchestrator_tickers.py` defaults `ta-fa` | Align with `phoenix-fa` or deprecate shim |

---

## 4. Target folder contracts

### `core/`

- **No imports from `agents/`** (except type-only if needed).
- Pure functions: load universe, merge masters, build confusion, write bundles.
- Unit-tested without Polygon/network where possible (fixtures).

### `agents/<name>/`

- **Public API:** `analyze(ticker: str, as_of_date: str) -> dict`
- **Adapter:** `to_envelope(native: dict) -> AgentEnvelope`
- **Forbidden:** import another agent package (except shared `core/`).

### `agents/orchestrator/`

- Registry maps `fusion_mode` → list of agent ids.
- Loads envelopes, calls existing `fusion_phoenix.py` / `fusion.py`.
- Does not fetch market data directly.

### `pipelines/`

- Input: CLI args or structured config dataclass.
- Output: file paths + summary dict (for Telegram/OpenClaw).
- May subprocess or thread sector jobs; uses `core/io` for merge.

### `apps/backtest-dashboard/`

- API routes list/load from `data/output/trading_runs/` via `core/io` helpers (optional thin wrapper).
- No fusion or scoring in TypeScript.

### `apps/openclaw/`

- Skills document exact shell/python commands.
- Scripts are one-liners to `run_trading.py` or `python -m pipelines.*`.

---

## 5. Pipeline specifications

### `pipelines/analyze`

**Input:** `--ticker`, `--date`, `--fusion` (phoenix-fa | phoenix | fundamental | ta-fa)  
**Output:** JSON stdout (OpenClaw) or file  
**Replaces:** Body of `run_trading.py analyze`, `openclaw/scripts/orchestrator_analyze.py`

### `pipelines/sector_pilot`

**Input:** `--sector`, `--signal-date`, `--eval-days`, `--output-dir`  
**Output:** `master_pilot.json` under output dir  
**Replaces:** `scripts/backtests/run_halal_sector_month_pilot.py`

### `pipelines/unified_pilot`

**Input:** `--signal-date`, `--eval-days`, `--merged-output`, optional `--sectors`  
**Output:** Merged `master_pilot.json`  
**Replaces:** `scripts/backtests/run_master_data_parallel_pilot.py`

### `pipelines/daily`

**Input:** `SIGNAL_DATE` env, flags for export/telegram  
**Output:** unified master + optional BUY excel + notify  
**Replaces:** `openclaw/scripts/run_daily_pipeline.sh` logic (shell keeps scheduling only)

---

## 6. TradingAgent skills (Phase 4)

Create under `AI-space/TradingAgent/skills/`:

### `trading-analyze/SKILL.md`

- Trigger: analyze, score, phoenix-fa, single ticker.
- Command: `run_trading.py analyze` or `pipelines/analyze`.

### `trading-sector-pilot/SKILL.md`

- Trigger: sector backtest, energy pilot, one sector.
- Command: `pipelines/sector_pilot --sector "Energy"`.

### `trading-unified-pilot/SKILL.md`

- Trigger: all sectors, master_pilot, pre-market.
- Command: `pipelines/unified_pilot`.

### `trading-dashboard/SKILL.md`

- Trigger: dashboard, phoenix-watch-buy, export BUY.
- Command: `npm run dev` in dashboard; `export_phoenix_buy_from_masters.py`.

Symlink or copy to `MyTradingSpace/openclaw/workspace/skills/`.

---

## 7. Backlog from TradingAgent prompts

Source: `AI-space/TradingAgent/prompts/prompts.md`

| Item | Phase | Action |
|------|-------|--------|
| Missing Jan–Mar predicted trends in 2025 JSON | 5 | Audit `_run_period` / `signal_correct`; ensure eval window in manifest |
| Dashboard misclassifications | 5 | Unify confusion bucket in `core/io`; single preprocessing before UI |
| Orchestrator vs technical signal rules | 0 | Spec audit doc in `TradingAgent/specs/` |
| Forecasting logic | 5+ | Separate spec; out of scope for isolation refactor unless bundled |

---

## 8. Testing strategy

| Layer | Tests |
|-------|--------|
| `core/` | Unit: merge, confusion, universe loaders |
| `agents/` | Unit: scoring; integration: analyze smoke with mocked data |
| `pipelines/` | Golden-file: small ticker list, compare master_pilot hash |
| Parity | AAPL 2026-05-15 phoenix-fa before/after refactor |
| OpenClaw | Skill dry-run: `orchestrator_analyze.sh` unchanged output |
| Dashboard | API returns new `unified_master_*` paths |

---

## 9. What we will not change

- Phoenix/FA scoring algorithms (unless backlog spec requires).
- `external-tools/` placement.
- OpenClaw model choice (Ollama qwen, etc.).
- Git remote / branch naming (team choice).
- Halal universe source files (`halal_sector_tickers.json`, `halal_tickers_clean.json`).

---

## 10. Success criteria

- [ ] Single command for analyze, sector pilot, unified pilot, daily pipeline.
- [ ] Zero scripts importing `agents.orchestrator.fusion*` outside orchestrator/pipelines.
- [ ] All agents pass envelope adapter tests.
- [ ] OpenClaw skills have no duplicated fusion code.
- [ ] Dashboard loads latest `unified_master_<date>` without manual path edits.
- [ ] `MODULE_MAP.md` updated to reflect `core/`, `pipelines/`, `apps/`.
- [ ] TradingAgent `specs/` is source of truth for contracts.

---

## 11. References

- Engineering workflow: `AI-space/AI-Brain/agent-skills/skills/spec-driven-development/SKILL.md`
- Meta skill discovery: `AI-space/AI-Brain/agent-skills/skills/using-agent-skills/SKILL.md`
- Current module map: `MyTradingSpace/MODULE_MAP.md`
