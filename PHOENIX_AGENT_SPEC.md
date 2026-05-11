# Phoenix Agent Spec

This file is normative for Phoenix Agent contracts. `docs/PHOENIX_AGENT_IMPLEMENTATION.md` keeps build history and rationale.

## Objective

Implement a standalone, deterministic Phoenix Trader agent that evaluates one ticker at one cutoff date using price structure, volume, Stage 2 trend context, entry/risk rules, and a 0-100 Phoenix score.

## Non-Goals

- Do not merge Phoenix into the TA+FA orchestrator graph.
- Do not add RSI, MACD, Bollinger Bands, Stochastics, or other rejected lagging indicators to Phoenix scoring.
- Do not use LLM output for scoring, pass/fail decisions, or backtest labels.
- Do not fetch data after the requested cutoff date for signal generation.

## Public API

- `agents.phoenix.service.analyze_ticker(ticker, as_of_date=None, settings=None, account_size=100_000) -> dict`
- `agents.phoenix.graph.build_graph(client=None, settings=None) -> compiled LangGraph runnable`
- `agents.phoenix.patterns.detect_all_patterns(snapshot, settings=None) -> PatternMatch`
- `agents.phoenix.filters.apply_hard_filters(snapshot, settings=None, raise_on_fail=False) -> FilterResult`
- `agents.phoenix.stage_classifier.classify_stage(snapshot, settings=None) -> StageResult`

## Graph Nodes

The Phoenix graph has eight nodes:

1. `fetch_data`
2. `apply_hard_filters`
3. `classify_stage`
4. `detect_patterns`
5. `evaluate_entry`
6. `compute_risk`
7. `build_score`
8. `render_report`

Expected fail-fast exits:

- Hard filter failure exits to `render_report` with `AVOID`.
- Non-Stage 2 exits to `render_report` when `PhoenixSettings.stage2_only` is true.

## JSON Output Keys

`analyze_ticker` returns a JSON-safe dict with these top-level keys:

- `ticker`
- `as_of_date`
- `signal`
- `score`
- `score_breakdown`
- `stage`
- `pattern`
- `entry`
- `risk`
- `hard_filter_passed`
- `hard_filter_reason`
- `report`
- `warnings`

`stage`, `pattern`, `entry`, and `risk` are nested dicts when applicable, otherwise `None` or an empty stage sentinel on error.

## Thresholds

All tunable values live in `agents/phoenix/config.py` on `PhoenixSettings`.

| Setting | Default | Contract |
| --- | ---: | --- |
| `volume_breakout_multiple` | `2.0` | Confirmed breakout volume must be at least 2x 20-bar average volume. |
| `volume_dryup_threshold` | `0.75` | Dry-up volume is below 75% of the comparison average. |
| `above_200dma_required` | `True` | Price must pass the 200-day SMA hard filter. |
| `above_52w_low_pct` | `0.50` | Price must be at least 50% above the 52-week low. |
| `stage2_only` | `True` | Non-Stage 2 names are not trade candidates. |
| `flat_base_max_range_pct` | `0.15` | Flat bases must stay within a 15% high-low range. |
| `vcp_max_contractions` | `3` | VCP scans up to three contractions. |
| `vcp_min_depth_pct` | `0.10` | VCP contractions must be at least 10% deep. |
| `vcp_contraction_ratio` | `0.50` | Successive VCP contractions must tighten by this ratio. |
| `flag_pole_min_gain_pct` | `8.0` | Tight flag pole must gain at least 8%. |
| `flag_max_retrace_pct` | `0.50` | Tight flag retrace may not exceed 50% of pole height. |
| `shakeout_max_bars_below` | `3` | Shakeout must recover quickly from support violation. |
| `pullback_proximity_pct` | `0.02` | Pullback must close within 2% of MA10 or MA20. |
| `buy_threshold` | `70.0` | Phoenix score at or above this value maps to `BUY`. |
| `watch_threshold` | `50.0` | Phoenix score at or above this value maps to `WATCH`; below maps to `AVOID`. |

## Pattern Priority

`detect_all_patterns` returns the highest-confidence candidate. Equal confidence is resolved by this priority order:

1. VCP
2. Flat Base
3. Tight Flag
4. Shakeout
5. Pullback

When no detector qualifies, return a `PatternMatch` with `pattern_name="None"`.

## Commands

Core verification:

```bash
pytest tests/
python -c "from agents.phoenix.patterns import detect_all_patterns; print(detect_all_patterns)"
```

Useful Phoenix scripts:

```bash
python scripts/run_orchestrator_tickers.py --tickers AAPL --date 2025-09-30 --strategy phoenix
python scripts/run_phoenix_sector_scan.py
python scripts/backtests/run_phoenix_polygon_nasdaq150_2025.py
python scripts/backtests/run_phoenix_fund_orchestrator_backtest_2025.py
```
