# Agent package template

Use this checklist when adding a new agent under `agents/<id>/`. Mirror **Phoenix** and **Fundamental** — do not refactor shared core modules.

## Required files

| File | Purpose |
|------|---------|
| `service.py` | Public entry: `analyze_ticker()` or `analyze_market()` |
| `config.py` | Settings dataclass + env loading |
| `models.py` | Request / snapshot dataclasses |
| `rules.py` | Deterministic scoring (no LLM in score path) |
| `data_client.py` or `fred_client.py` | Agent-local API client |
| `graph.py` | LangGraph: fetch → evaluate → render |
| `reporting.py` | Human-readable `report` string |
| `adapter.py` | Re-export envelope helper |
| `exceptions.py` | Agent-specific errors (optional) |

## Integration (additive only)

1. `agents/orchestrator/agent_envelope.py` — add `envelope_from_<id>()`
2. `core/contracts/envelope.py` — re-export envelope helper
3. `agents/_registry.py` — add `AgentSpec`
4. `docs/specs/<ID>_AGENT_SPEC.md` — spec document
5. `cli/__main__.py` — extend `agent` subcommand choices when ready

## Do not

- Modify Phoenix or Fundamental packages for new agent needs
- Change default `phoenix-fa` fusion or daily pipeline without explicit opt-in
- Put agent-specific HTTP clients in `core/data/` (keep clients inside the agent folder)
- Use LLM output to set scores (LLM = post-score bullets only)

## Data sources

- **OHLCV / profile:** import `agents.polygon_data.PolygonClient`
- **Fundamentals for FA:** unchanged — use existing Fundamental agent
- **Macro:** FRED inside `agents/macro/` only
- Record `extras.data_sources[]` on every envelope for auditability

## Test

```bash
pytest tests/test_<id>.py
./bin/mts agent <id> --date YYYY-MM-DD
```
