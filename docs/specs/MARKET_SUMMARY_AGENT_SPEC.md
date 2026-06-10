# Market Summary Agent Spec

**Agent ID:** `market_summary`  
**Scope:** Session (market-wide)  
**Entry:** `agents.market_summary.service.analyze_market(as_of_date)`

## Purpose

Daily market-wide briefing: VIX regime, SPY trend, sector ETF rotation vs SPY, composed with macro agent output.

## Data sources

| Source | Symbols | Use |
|--------|---------|-----|
| Polygon | `I:VIX`, `SPY`, `XLC`…`XLU` | OHLCV, 5d/20d returns |
| Macro agent | internal call | Fed/CPI/curve context |

**Env:** `POLYGON_API_KEY`, `FRED_API_KEY` (via macro sub-call)

## Output

Native dict keys include: `market_wide_signal`, `vix`, `vix_regime`, `sector_leaders`, `sector_laggards`, `macro`, `bullets`, `data_sources`.

Envelope via `envelope_from_market_summary()`.

## VIX regimes

| Regime | VIX level |
|--------|-----------|
| low | &lt; 15 |
| normal | 15–20 |
| fear | 20–30 |
| extreme | ≥ 30 |

Extreme VIX caps `market_wide_signal` to neutral/bearish overlay.

## CLI

```bash
./bin/mts agent market_summary --date 2026-06-01
./bin/mts context --date 2026-06-01
```

## Design rules

- Composes macro via `analyze_market()` — does not duplicate FRED logic
- Does not modify Phoenix, Fundamental, or fusion defaults
