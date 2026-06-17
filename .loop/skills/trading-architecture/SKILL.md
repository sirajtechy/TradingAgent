---
name: trading-architecture
description: Apply MyTradingSpace architecture rules for agents, orchestrator, data flow, Phoenix, and CLI boundaries. Use when reviewing or implementing loop features.
---

# Trading Architecture Skill

## Principles

- Keep research, signal generation, risk, and execution concerns separated
- Phoenix + FA core scoring logic changes require quant-risk review
- Orchestrator fusion lives in `agents/orchestrator/` — one orchestrator, not a second brief agent
- Human decision mode: `agent_breakdown` is primary; advisory verdict is reference only
- Prefer typed contracts between agents (`envelope`, `FusionResult`)
- Preserve observability: `data_sources`, warnings, reports on every agent

## Module map

| Area | Path |
|------|------|
| Agents | `agents/<name>/` |
| Orchestrator | `agents/orchestrator/` |
| CLI | `cli/`, `bin/mts` |
| Pipelines | `pipelines/` |
| Tests | `tests/` |
| Journals | `Trading-Journals/` |
| Loop | `.loop/` |

## Review checks

- Did this blur analysis vs execution?
- Did it introduce hidden prompt coupling or LLM-only paths without deterministic fallback?
- Did it weaken logging, explainability, or backtest replayability?
