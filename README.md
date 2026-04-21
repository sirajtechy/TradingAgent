# MyTradingSpace — Multi-Agent Stock Analysis Platform

A deterministic, rule-based multi-agent system for analyzing stocks using both fundamental and technical analysis. Three specialized agents work independently and can be fused via an Orchestrator to produce higher-confidence trade signals. Designed for backtesting, halal-universe screening, and live prediction workflows.

---

## What This Application Does

Given a **ticker**, a **cutoff date**, and a **target holding period**, the platform:

1. Runs a **Fundamental Agent** to score the company's financial health, valuation, quality, and growth using six established frameworks
2. Runs a **Technical Agent** to score price action across nine momentum and trend-following frameworks
3. Optionally fuses both signals via an **Orchestrator** using Confidence-Weighted Asymmetric Fusion (CWAF)
4. Returns a structured trade recommendation (BUY / SELL / HOLD) with entry price, stop-loss, target, and exit outcome
5. Exports results to Excel and JSON for analysis and dashboard rendering

All scoring is **100% deterministic and rule-based** — no LLM influences any score or pass/fail decision.

---

## Architecture Overview

```
MyTradingSpace/
├── agents/
│   ├── fundamental/       # Fundamental Agent v3 — 6 scoring frameworks
│   ├── technical/         # Technical Agent v2 — 9 scoring frameworks
│   ├── orchestrator/      # CWAF Orchestrator — fuses both agents
│   ├── oneil/             # O'Neil-style stage analysis (breakout patterns)
│   └── polygon_data/      # Shared Polygon.io OHLCV data client
├── backtests/             # Backtest runners per agent
├── scripts/               # Batch prediction and backtest scripts
├── backtest-dashboard/    # Next.js dashboard for visualizing results
├── data/
│   ├── input/             # Halal universe lists, sector tickers
│   └── output/            # Backtest Excel files, JSON results, reports
└── agent_learning/        # Steering docs, analytical memory, brain notes
```

---

## The Three Agents

### 1. Fundamental Agent (v3)

Evaluates a company's financials using six academically-sourced frameworks. All data is fetched point-in-time from Financial Modeling Prep (FMP).

| Framework | Category | Weight |
|-----------|----------|--------|
| Piotroski F-Score | Financial Health | 12.5% |
| Altman Z-Score | Financial Health | 12.5% |
| Graham / Buffett | Valuation | 15% |
| Lynch Fair Value (PEG) | Valuation | 15% |
| Greenblatt Magic Formula | Quality | 25% |
| Growth Profile (CAGR) | Growth | 20% |

**Signal mapping:** Composite score ≥70 → Bullish · 40–69 → Neutral · <40 → Bearish  
**12-month backtest (60 tickers):** 57.1% win rate · 74% abstention rate · Precision 60.6%

---

### 2. Technical Agent (v2)

Evaluates price action using nine indicator frameworks sourced from Polygon.io OHLCV data.

| Framework | Weight |
|-----------|--------|
| EMA Trend Alignment | 17% |
| MACD System | 14% |
| RSI Regime | 14% |
| Ichimoku Cloud | 12% |
| Bollinger Bands | 10% |
| Volume (OBV + CMF) | 10% |
| Pattern Recognition | 8% |
| Momentum Composite (ROC + Williams %R + CCI) | 8% |
| ADX + Stochastic | 7% |

**Signal mapping:** Score ≥60 → Bullish · 35–59 → Mixed · <35 → Bearish  
**12-month backtest (Tech + Energy sectors):** 57.0% win rate · 19.6% abstention · Precision 60.6%

---

### 3. Orchestrator — CWAF (Confidence-Weighted Asymmetric Fusion)

Combines both agents using their confidence levels to resolve agreement, conflict, and edge cases. The Fundamental Agent is conservative (74% abstention); the Technical Agent is more aggressive (19.6% abstention). CWAF preserves each agent's confidence signal rather than simple majority voting.

**12-month backtest (5 sectors, 600 periods):** 52.0% win rate · Financials sector: 71.1% win rate · Agent agreement rate: 49.3%

---

## Covered Universe

60 tickers across 5 sectors used for backtesting:

| Sector | Tickers |
|--------|---------|
| Technology | AAPL, MSFT, NVDA, GOOGL, META, AMZN, TSLA, ORCL, ANET, CRM, AMD, INTC |
| Healthcare | JNJ, UNH, LLY, ABBV, MRK, PFE, BMY, CVS, CI, MDT, ABT, HUM |
| Financials | JPM, BAC, WFC, GS, MS, V, MA, AXP, BLK, C, USB, PNC |
| Consumer Staples | PEP, KO, PG, WMT, COST, MCD, PM, MO, GIS, K, CL, CLX |
| Energy | XOM, CVX, COP, SLB, OXY, PSX, VLO, MPC, EOG, HAL, BKR, DVN |

A separate **halal universe** is also maintained for Shariah-compliant screening.

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_halal_predictions.py` | Primary batch prediction runner — outputs Excel + JSON |
| `scripts/run_backtest_excel.py` | Runs full backtest and exports to Excel |
| `scripts/run_live_predictions.py` | Live prediction mode using today's data |
| `backtests/run_fundamental.py` | Standalone fundamental agent backtest |
| `backtests/run_technical.py` | Standalone technical agent backtest |
| `backtests/run_orchestrator.py` | Full orchestrator CWAF backtest |

---

## Backtest Dashboard

A Next.js web dashboard (`backtest-dashboard/`) visualizes backtest results, trade logs, sector breakdowns, and confusion matrices. Deployed to Vercel.

---

## Environment Setup

```bash
# Python dependencies (from workspace venv)
source /path/to/.venv/bin/activate

# Required API keys
export FMP_API_KEY=your_fmp_key        # Financial Modeling Prep (fundamental agent)
export POLYGON_API_KEY=your_poly_key   # Polygon.io (technical agent + OHLCV data)
```

---

## Running Predictions

```bash
# Batch prediction — halal sector universe, cutoff date, 20-day target
python scripts/run_halal_predictions.py --universe sectors --date 2025-12-31 --target-days 20 --workers 4

# Full backtest export to Excel
python scripts/run_backtest_excel.py --date 2025-12-31 --workers 4 --target-days 20

# Run tests
python -m pytest -q
```

---

## Important Limitations

- Scores are labeled **experimental** — designed for backtesting research, not proven live trading signals.
- The Shariah purity screen uses `interestIncome / revenue` as a proxy — not a full business-segmentation model.
- Historical sector/industry metadata is pulled from current FMP profile endpoints (no point-in-time snapshot available).
- Forward analyst estimates are excluded from Lynch calculations to preserve point-in-time reproducibility.
