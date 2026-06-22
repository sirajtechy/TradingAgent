# Documentation Index

All project documentation is organized in this folder.

## Quick Reference

| Document | Purpose |
|----------|---------|
| [SCRIPTS.md](./SCRIPTS.md) | All commands and scripts |
| [STRUCTURE.md](./STRUCTURE.md) | Project folder layout |
| [MODULE_MAP.md](./MODULE_MAP.md) | Feature → module mapping |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |

## Architecture (with Mermaid diagrams)

| Document | Purpose |
|----------|---------|
| [architecture/ARCHITECTURE.md](./architecture/ARCHITECTURE.md) | System diagrams (flowcharts) |
| [architecture/SCENARIOS.md](./architecture/SCENARIOS.md) | Usage scenarios (sequence diagrams) |
| [architecture/CONFIG.md](./architecture/CONFIG.md) | Configuration reference |

## Specifications

| Document | Purpose |
|----------|---------|
| [specs/ORCHESTRATOR_MODES.md](./specs/ORCHESTRATOR_MODES.md) | Fusion modes (phoenix-fa, ta-fa) |
| [specs/PHOENIX_AGENT_SPEC.md](./specs/PHOENIX_AGENT_SPEC.md) | Phoenix agent specification |
| [specs/FUNDAMENTAL_AGENT_SPEC.md](./specs/FUNDAMENTAL_AGENT_SPEC.md) | Fundamental agent specification |
| [specs/ORCHESTRATOR_DESIGN.md](./specs/ORCHESTRATOR_DESIGN.md) | Orchestrator design |
| [specs/PIPELINES.md](./specs/PIPELINES.md) | Pipeline architecture |
| [specs/ADR-001-agent-envelope.md](./specs/ADR-001-agent-envelope.md) | Agent envelope ADR |

## Guides

| Document | Purpose |
|----------|---------|
| [BACKTEST_PLAYBOOK.md](./BACKTEST_PLAYBOOK.md) | How to run backtests |
| [BACKTEST_OUTPUT_FORMAT.md](./BACKTEST_OUTPUT_FORMAT.md) | Output JSON schemas |
| [PHOENIX_AGENT_IMPLEMENTATION.md](./PHOENIX_AGENT_IMPLEMENTATION.md) | Phoenix implementation details |
| [MULTI_AGENT_CONTRACT.md](./MULTI_AGENT_CONTRACT.md) | Multi-agent integration |
| [REFACTOR_GUARDRAILS.md](./REFACTOR_GUARDRAILS.md) | Refactoring guidelines |

## Plans

| Document | Purpose |
|----------|---------|
| [planned-unified-technical-agent.md](./planned-unified-technical-agent.md) | **Active** — unified Technical Agent (Phoenix + 4 strategies), enrichment gating, matrix layers |
| [confusion-matrix-backtest-plan.md](./confusion-matrix-backtest-plan.md) | **Active** — multi-agent confusion matrix, PIT audit, implementation phases |
| [planned-atr-sma50-exit-ladder.md](./planned-atr-sma50-exit-ladder.md) | DEFERRED — ATR/SMA50 scale-out exit rules |
| [planned-151-trading-strategies.md](./planned-151-trading-strategies.md) | DEFERRED — SSRN 151-strategies catalog map |
| [plans/PRODUCTION_PLAN.md](./plans/PRODUCTION_PLAN.md) | Production roadmap |
| [plans/REFACTOR_PLAN.md](./plans/REFACTOR_PLAN.md) | Refactor plan |
| [plans/README.md](./plans/README.md) | Plans overview |

## Agent Learning

| Document | Purpose |
|----------|---------|
| [agent-learning/steering.md](./agent-learning/steering.md) | Agent steering guide |
| [agent-learning/backtesting-complete-guide.md](./agent-learning/backtesting-complete-guide.md) | Backtesting guide |
| [agent-learning/trading-analysis-mistakes.md](./agent-learning/trading-analysis-mistakes.md) | Common mistakes |

## Strategies

| Document | Purpose |
|----------|---------|
| [strategies/phoneix-trader.md](./strategies/phoneix-trader.md) | Phoenix trading strategy |

## Data Contracts

- **Input:** `data/input/master_data/` — halal universe, sector tickers
- **Output:** `data/output/trading_runs/` — master_pilot.json, run_bundle.json
- **Committed:** source code, docs, `data/input/master_data/`
- **Gitignored:** `data/output/`, `data/archive/`
