# Sentiment Agent Spec

**Agent ID:** `sentiment`  
**Scope:** Per ticker (aggregator)  
**Entry:** `agents.sentiment.service.analyze_ticker(ticker, as_of_date)`

## Purpose

Normalized multi-dimension sentiment score. Consumes outputs from News, Insider, and Macro agents, combines them into a single 0-100 score with per-dimension breakdown.

## Dimensions

| Dimension | Source agent | Default weight |
|-----------|-------------|----------------|
| News | `agents.news` | 30% |
| Analyst | News subscore (`analyst_grades`) | 25% |
| Insider | `agents.insider` | 20% |
| Macro | `agents.macro` | 15% |
| Geopolitics | Placeholder (Phase C) | 10% |

Weights are configurable via `SentimentSettings`.

## Output

Native dict keys: `signal`, `score`, `sentiment` (positive/neutral/negative), `band`, `confidence`, `subscores`, `dimensions` (per-dimension signal map), `ohlcv_context`, `bullets`, `data_sources`, `report`.

Envelope via `envelope_from_sentiment()`.

## CLI

```bash
./bin/mts agent sentiment --ticker AAPL --date 2026-06-01
```

## Design rules

- Calls News, Insider, Macro agents internally; each wrapped in try/except for graceful degradation
- Adds Polygon OHLCV context (close, 5d change) via `agents.polygon_data`
- Geopolitics dimension wired as neutral placeholder until Phase C
- No LLM — deterministic weighted aggregation only
- Abstains only when zero dimension data is available
