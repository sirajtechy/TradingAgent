# Module Map

Minimal map from user-facing feature areas to specs, modules, tests, and scripts.

## Implementation priorities (near-term focus)

Prioritize work on **Orchestrator**, **Fundamental**, and **Phoenix** — specs, fusion modes, regression backtests, and agent contracts. Treat the **Technical** agent mainly as stable input to the orchestrator: fix breakage that blocks CWAF fusion or backtests, but defer standalone TA refactors / new TA frameworks unless they directly support orchestrator roadmap.

See also `docs/MULTI_AGENT_CONTRACT.md` for how future signals fit the same orchestration pattern.

## Repository layout

Feature-oriented tree: [STRUCTURE.md](./STRUCTURE.md). Specs live under `docs/specs/`.

## Canonical CLI — prefer this over new scripts

| Purpose | Command |
| --- | --- |
| **Point-in-time analysis** (Phoenix+FA default, TA+FA, Phoenix-only, or compare) | `python scripts/run_trading.py analyze ...` |
| **Agnostic pipelines** (OpenClaw, daily, sector/unified pilots) | `python -m pipelines analyze\|sector\|unified\|daily ...` |
| **Monthly / heavy backtests** (reuse existing engines; no duplicate logic) | `python scripts/run_trading.py backtest --engine <alias> -- ...` |

When prompting an assistant: **extend `scripts/run_trading.py` flags or `BACKTEST_ENGINES` aliases** instead of adding another `scripts/backtests/run_*2025.py` unless there is genuinely new methodology.

**Primary orchestration path you described:** `--fusion phoenix-fa` runs Fundamental + Phoenix and CWAF-fuses via `fuse_signals_phoenix` / `FusionMode.PHOENIX_FUND`.

Universe selection flags: `--tickers`, `--sector` (legacy 5-sector list), `--halal-sector` (+ optional `--halal-limit`), **`--halal-universe top10|full`** (full = `halal_sector_tickers.json` for large sector batches), `--halal-sectors` with `--random-sample` for random batches.

`scripts/run_orchestrator_tickers.py` remains a **thin shim** (defaults to TA+FA for backward compatibility).

---

| Feature | Spec / Docs | Module | Tests | Scripts |
| --- | --- | --- | --- | --- |
| Phoenix Agent | `docs/specs/PHOENIX_AGENT_SPEC.md`, `docs/PHOENIX_AGENT_IMPLEMENTATION.md` | `agents/phoenix/` | `tests/phoenix/test_patterns_and_filters.py`, `tests/phoenix/test_scoring.py` | `scripts/run_trading.py analyze --fusion phoenix` or `--fusion phoenix-fa`, `scripts/run_phoenix_sector_scan.py` |
| Phoenix Patterns | `docs/specs/PHOENIX_AGENT_SPEC.md` | `agents/phoenix/patterns/`, `agents/phoenix/pattern_helpers.py` | `tests/phoenix/test_patterns_and_filters.py` | Import smoke command in spec |
| Fundamental Agent | `docs/specs/FUNDAMENTAL_AGENT_SPEC.md` | `agents/fundamental/` | Exercised via orchestrator tests + FA-specific scripts | Fundamental CLI / data scripts as wired in README |
| Standard TA+FA Orchestrator | `docs/specs/ORCHESTRATOR_DESIGN.md`, `docs/specs/ORCHESTRATOR_MODES.md` | `agents/orchestrator/graph.py`, `agents/orchestrator/fusion.py`, `agents/orchestrator/service.py`, `agents/orchestrator/modes.py`, `agents/orchestrator/agent_envelope.py` | `tests/test_fusion.py`, `tests/test_conflict_resolution.py`, `tests/test_orchestrator_graph.py`, `tests/orchestrator/test_modes_and_envelope.py` | `scripts/run_trading.py analyze --fusion ta-fa`, shim `scripts/run_orchestrator_tickers.py` |
| Technical Agent | `prompts/tech-agent.md`, `docs/agent-learning/technical_agent/steering.md` | `agents/technical/` | `tests/test_technical_*.py` (maintenance / blockers only per priorities above) | `scripts/run_*` invoking TA standalone |
| Phoenix+FA Fusion Backtest | `docs/specs/ORCHESTRATOR_MODES.md`, `docs/BACKTEST_PLAYBOOK.md` | `agents/orchestrator/fusion_phoenix.py`, `agents/orchestrator/backtest_phoenix.py` | Existing `tests/` coverage plus Phoenix unit tests | `scripts/run_trading.py backtest --engine phoenix-fund-2025 -- ...`, or `scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py` directly |
| Backtest Outputs | `docs/BACKTEST_OUTPUT_FORMAT.md`, `docs/BACKTEST_PLAYBOOK.md` | `backtests/common.py`, `core/io/`, `agents/orchestrator/backtest_phoenix.py` | Existing `tests/` coverage | `scripts/backtests/*.py`, `python -m pipelines` |
| Pipelines / OpenClaw | `docs/specs/PIPELINES.md`, `openclaw/README.md` | `pipelines/`, `core/` | Manual smoke | `python -m pipelines`, `openclaw/scripts/` |
| Future Agent Integration | `docs/MULTI_AGENT_CONTRACT.md` | `agents/_registry.py`, future `agents/*/` adapters | Adapter-specific synthetic tests | TBD per agent |
| Trading run bundles + UI | `docs/BACKTEST_PLAYBOOK.md` § run_bundle | `scripts/lib/run_bundle.py`, `scripts/run_trading.py` (`compare`) | Manual / integration | `backtest-dashboard` → `/trading-runs` |
