# Geopolitics Agent Spec

**Agent ID:** `geopolitics`  
**Scope:** Session (market-wide)  
**Entry:** `agents.geopolitics.service.analyze_market(as_of_date)`

## Purpose

Scan FMP general and forex news for geopolitical risk keywords, score density and concentration, optionally classify via LLM.

## Data sources

| Endpoint | FMP path | Use |
|----------|----------|-----|
| General news | `/stable/news/general-latest` | Keyword scan |
| Forex news | `/stable/news/forex-latest` | Currency/trade risk |

**Env:** `FMP_API_KEY` (required), `OPENAI_API_KEY` (optional for LLM), `LLM_ENABLED` (default true)

## Scoring

| Component | Weight | Rule |
|-----------|--------|------|
| Keyword density | 45% | More geo-keyword matches = higher risk (lower score) |
| Headline concentration | 30% | % of scanned headlines that are geo-relevant |
| LLM classification | 25% | Bounded +-8pt adjustment from LLM sentiment |

Without LLM, scoring is fully deterministic (keyword density + concentration only).

## Sector exposure map

Identifies which sectors are most affected based on keyword-to-sector mapping: Energy, IT, Industrials, Financials, Materials.

## CLI

```bash
./bin/mts agent geopolitics --date 2026-06-01
./bin/mts context --date 2026-06-01
```

## Design rules

- Keyword pre-filter is deterministic; LLM is a bounded post-score overlay
- `LLM_ENABLED=false` disables LLM; score remains fully deterministic
- LLM results cached in `data/output/llm_cache/` (gitignored)
- Wired into Sentiment agent as the geopolitics dimension
