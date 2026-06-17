# Portfolio Engine Spec

Normative spec for the halal portfolio intelligence layer (`agents/portfolio/`).

## Purpose

Evolve MyTradingSpace from per-ticker BUY/WATCH signals into a **portfolio book**:

- Cross-sectional momentum rank (video-style FRR)
- Multi-agent conviction blend (Phoenix, FA, strategies)
- Monthly rebalance + bear regime → cash
- Sigma-Scanner-style backtest outputs (CAGR, drawdown, monthly CSV, trade history)

Production default unchanged: `./bin/mts daily` = Phoenix + FA only.

## Commands

```bash
# Backtest (fast pilot universe)
./bin/mts portfolio backtest --start 2024-01-01 --end 2025-12-31 --budget 200000 --universe top10

# Live advisory book (~20 names, USD sizing)
./bin/mts portfolio allocate --budget 200000 --date 2026-06-13 --universe top10

# Fast full-agents book (~3-5 min): top 10 momentum names get full agent scores; 20-name portfolio from rank blend
./bin/mts portfolio allocate --budget 200000 --full-agents --enrich-max 10 --enrich-workers 8
```

## Rules (defaults in `data/config/portfolio_rules.json`)

| Rule | Default |
|------|---------|
| Budget | 200,000 |
| Names | 20 |
| Rebalance | 21st of month |
| Exit rank | Top 10% of universe (FRR) |
| Sector cap | 25% |
| Regime | Weekly Supertrend on SPY → 100% cash |
| Universe | `top10` per sector (pilot) or `full` halal |

## Conviction formula

```
conviction =
  25% cross_sectional_momentum
+ 20% phoenix_fusion_score
+ 20% strategy_blend_score
+ 15% intelligence_consensus
+ 10% relative_strength_vs_spy
+ 10% smoothness
```

Momentum core: weighted (1M + 6M + 9M) returns ÷ 3M volatility.

## Anti-lookahead

- Backtest uses Polygon PIT bars only (`as_of_date` filter)
- Web research tier disabled in backtest (future)
- Agent enrichment optional (`--enrich-agents`); top-N only
- `--full-agents` pre-warms session context once, then enriches top N tickers in parallel (`--enrich-workers`, default 8). Default `--enrich-max` is 10 for full-agents (30 otherwise); portfolio size (`--num-stocks`) can exceed enrich cap — names outside top N use momentum-only conviction

## Outputs

| File | Path |
|------|------|
| Summary | `data/output/portfolio_backtests/<run_id>/summary.json` |
| Monthly | `.../monthly_returns.csv` |
| Trades | `.../trade_history.csv` |
| Live book | `data/output/portfolio_allocations/holdings_<date>.json` |

## Phase roadmap

- **v1 (this branch):** momentum + optional strategy enrich, monthly FRR, regime cash
- **v2:** intraday swing overlay (Breitstein 1h), `./bin/mts risk` sizing
- **v3:** FULL_CONTEXT intelligence attribution batch on candidates
