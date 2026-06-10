# Macroeconomics Agent Spec

**Agent ID:** `macro`  
**Scope:** Session (market-wide)  
**Entry:** `agents.macro.service.analyze_market(as_of_date)`

## Purpose

Deterministic macro backdrop for ~1-month swing trades using FRED data at a point-in-time cutoff.

## Data sources

| Series | FRED ID | Use |
|--------|---------|-----|
| Fed Funds | `DFF` | Rate level / direction |
| CPI | `CPIAUCSL` | YoY inflation trend |
| Unemployment | `UNRATE` | Labor market |
| Yield curve | `T10Y2Y` | 10Y−2Y spread |

**Env:** `FRED_API_KEY` (required)

## Output

Native dict keys: `signal`, `score`, `band`, `confidence`, `subscores`, `metrics`, `bullets`, `data_sources`, `warnings`, `report`.

Envelope via `envelope_from_macro()`.

## CLI

```bash
./bin/mts agent macro --date 2026-06-01
./bin/mts context --date 2026-06-01
```

## Design rules

- Deterministic scoring in `rules.py` — no LLM in Phase A
- FRED `observation_end=as_of_date` for point-in-time integrity
