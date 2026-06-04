# Orchestrator Modes

This repo currently supports three related but distinct execution modes.

## TA + FA Graph

The standard orchestrator runs the Technical Agent and Fundamental Agent, then fuses their normalized outputs with Confidence-Weighted Asymmetric Fusion.

Key files:

- `agents/orchestrator/graph.py` builds the LangGraph workflow.
- `agents/orchestrator/fusion.py` implements the TA+FA fusion rules.
- `agents/orchestrator/service.py` exposes the public `analyze_ticker` entry point.
- `scripts/run_orchestrator_tickers.py` runs explicit tickers or sectors with `--strategy orchestrator`.

## Standalone Phoenix CLI

Phoenix remains a standalone agent with its own graph, settings, pattern detectors, score, report, and public API. It is not merged into the standard TA+FA graph.

Key files:

- `agents/phoenix/service.py` exposes `analyze_ticker`.
- `agents/phoenix/graph.py` defines the Phoenix eight-node graph.
- `agents/phoenix/patterns/` contains the structural pattern detectors.
- `scripts/run_orchestrator_tickers.py` runs Phoenix with `--strategy phoenix`.
- `scripts/run_phoenix_sector_scan.py` supports Phoenix sector scanning.

## Phoenix + FA Backtest Fusion

This mode replaces the Technical Agent input with Phoenix, then reuses the orchestrator fusion schema to combine Phoenix with the Fundamental Agent.

Key files:

- `agents/orchestrator/fusion_phoenix.py` normalizes Phoenix output and fuses Phoenix + FA.
- `agents/orchestrator/backtest_phoenix.py` runs Phoenix + FA monthly backtests.
- `scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py` is the primary Phoenix + FA backtest runner.
- `scripts/backtests/run_phoenix_orchestrator_backtest_2025.py` supports Phoenix orchestrator backtest runs.

Fusion weights for this path are **not** the same as TA+FA: `fuse_signals_phoenix` reads `OrchestratorSettings.phoenix_fund_weights`, which defaults to roughly **90% Phoenix / 10% Fundamental** on agreement-style blends so the orchestrator score is Phoenix-dominant. TA+FA continues to use `OrchestratorSettings.weights`. Both tables remain dataclass fields so future agents can plug in configurable presets.

## Mode Boundary

- Use TA+FA graph for the main production orchestrator path.
- Use standalone Phoenix when evaluating the Phoenix Trader strategy alone.
- Use Phoenix+FA backtest fusion for experiments comparing Phoenix against the current Technical Agent in a fused setting.

## Programmatic fusion dispatch

`agents/orchestrator/modes.py` exposes `FusionMode` (`TECH_FUND`, `PHOENIX_FUND`) and `fuse_by_mode(...)` — a thin switch over `fuse_signals` versus `fuse_signals_phoenix` so backtests and services do not scatter stringly-typed branching.

Unified logging / manifests can use envelope dicts built by `agents/orchestrator/agent_envelope.py` (see `docs/MULTI_AGENT_CONTRACT.md`).

## Recommended entry point

For **one-off analysis** with Phoenix+Fundamental fusion (CWAF), use:

`python scripts/run_trading.py analyze --fusion phoenix-fa --date YYYY-MM-DD --tickers ...`

See `MODULE_MAP.md` → Canonical CLI for universe flags (halal sectors, random samples).
