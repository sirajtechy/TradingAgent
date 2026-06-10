# Insider Trades Agent Spec

**Agent ID:** `insider`  
**Scope:** Per ticker  
**Entry:** `agents.insider.service.analyze_ticker(ticker, as_of_date)`

## Purpose

Deterministic scoring of insider buy/sell activity from FMP, with emphasis on cluster buys and executive-level signals.

## Data sources

| Endpoint | FMP path | Use |
|----------|----------|-----|
| Insider trades | `/stable/insider-trading` | Buy/sell transactions |

**Env:** `FMP_API_KEY` (required)

## Scoring weights

| Component | Weight | Rule |
|-----------|--------|------|
| Net activity | 40% | Buy $ vs sell $ ratio |
| Cluster buys | 30% | Multiple unique buyers = stronger signal |
| Executive signal | 30% | CEO/CFO/Director buys vs sells |

## Output

Native dict keys: `signal`, `score`, `band`, `confidence`, `subscores`, `metrics` (buy_count, sell_count, net_value), `bullets`, `data_sources`, `report`.

Envelope via `envelope_from_insider()`.

## CLI

```bash
./bin/mts agent insider --ticker AAPL --date 2026-06-01
```

## Design rules

- Point-in-time: `filingDate <= as_of_date`, lookback 90 days by default
- No LLM — fully deterministic
- Abstains when zero trades found in lookback window
