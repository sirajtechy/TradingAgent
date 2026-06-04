# ADR-001: Agent envelope contract

**Status:** Accepted  
**Date:** 2026-05-23

## Context

Multiple agents (Phoenix, Fundamental, Technical) produce native JSON. Fusion and dashboards need a stable, agent-agnostic shape.

## Decision

All agents expose:

1. **Native analyze:** `analyze_ticker(ticker, as_of_date, ...) -> dict`
2. **Envelope adapter:** `envelope_from_<agent>(native, ...) -> AgentEnvelope dict`

Canonical envelope fields match `MyTradingSpace/docs/MULTI_AGENT_CONTRACT.md`:

| Field | Type | Notes |
|-------|------|-------|
| agent_id | string | e.g. `phoenix` |
| as_of_date | string | ISO date |
| signal | string | bullish / bearish / neutral |
| score | number | 0–100 |
| confidence | string | low / medium / high |
| band | string | poor / fair / good / excellent |
| abstain | bool | true if agent cannot score |
| reason | string? | abstain or warning |
| data_quality | string | good / fair / poor / unknown |
| warnings | list | free-form strings |
| extras | object | agent-specific (subscores, etc.) |

Implementation source (unchanged): `agents/orchestrator/agent_envelope.py`.

New code imports envelopes via `core.contracts.envelope` (shim re-export).

## Fusion modes (production)

| Mode | Agents | Entry |
|------|--------|-------|
| phoenix-fa | Phoenix + Fundamental + CWAF | `pipelines.analyze`, `run_trading.py analyze` |
| phoenix | Phoenix only | same |
| fundamental | FA only | same |
| ta-fa | LangGraph TA+FA | same (not Phoenix path) |

Fusion logic stays in `agents/orchestrator/modes.py` (`fuse_by_mode`).

## Consequences

- Pipelines and OpenClaw must not duplicate fusion branches; they call `pipelines.analyze`.
- Future agents add `agents/<id>/adapter.py` + `agents/_registry.py` entry only.
- `core/` must not import agent implementations (contracts are shims until full extraction).
