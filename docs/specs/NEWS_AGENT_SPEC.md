# News Analyst Agent Spec

**Agent ID:** `news`  
**Scope:** Per ticker  
**Entry:** `agents.news.service.analyze_ticker(ticker, as_of_date)`

## Purpose

Deterministic scoring of recent headlines, analyst grades (GS/MS priority), and price target direction from FMP.

## Data sources

| Endpoint | FMP path | Use |
|----------|----------|-----|
| Stock news | `/stable/news/stock` | Headline volume |
| Analyst grades | `/stable/grades` | Upgrade/downgrade counts, priority firm filter |
| Price targets | `/stable/price-target` | Consensus PT vs current close |

**Env:** `FMP_API_KEY` (required), `POLYGON_API_KEY` (optional, for current close)

## Scoring weights

| Component | Weight | Rule |
|-----------|--------|------|
| Headline volume | 20% | More headlines = more attention |
| Analyst grades | 45% | Net upgrades/downgrades + GS/MS priority bonus |
| Price target direction | 35% | Avg PT upside vs current close |

## Output

Native dict keys: `signal`, `score`, `band`, `confidence`, `subscores`, `headline_count`, `upgrades`, `downgrades`, `priority_actions`, `bullets`, `data_sources`, `report`.

Envelope via `envelope_from_news()`.

## CLI

```bash
./bin/mts agent news --ticker AAPL --date 2026-06-01
```

## Design rules

- Point-in-time: `publishedDate <= as_of_date`
- Priority firms (GS, MS) configurable via `NewsSettings.priority_firms`
- No LLM in Phase B — deterministic headline/grade rules only
