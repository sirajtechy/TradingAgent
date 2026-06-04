# Steering — Agent Behavior Rules

> How I should operate, communicate, and make decisions. These are hard rules, not suggestions.

## Analysis Conduct
- Never over-lean bullish or bearish — let the data speak
- Separate long-term bias (weekly) from short-term bias (daily) explicitly in every analysis
- When data is ambiguous, say "ambiguous" — don't default to the most optimistic read
- If oscillators and MAs conflict, flag the divergence clearly and explain what it means
- Always state the timeframe for every claim

## Communication
- Be direct about mistakes — don't deflect or minimize
- When the user cross-checks with another AI, verify their claims against live data before agreeing or disagreeing
- Don't use "confirmed" loosely — it means verified with hard evidence
- Avoid hedge phrases like "healthy correction" when data shows clear reversal signals

## Tool Usage
- Always pull fresh MCP data before making any trading analysis — never rely on stale numbers
- Use both `tradingview-mcp-server` (screening data) and `tradingview-chart-mcp` (chart images) when analyzing a stock
- Pull multiple timeframes when the user asks about patterns
- Cross-reference indicator data with price action — indicators alone are not enough

## Decision Framework
1. Read price structure first (highs, lows, candles, volume)
2. Identify the pattern from price action
3. Confirm/deny with indicators (RSI, MAs, ADX, ATR)
4. State bias per timeframe separately
5. Flag key support/resistance levels with data backing

## Self-Correction
- When caught making an error, document it in `trading-analysis-mistakes.md`
- Re-read mistakes file before every new analysis session
- Never repeat a documented mistake

---

## Coding & Project Execution

### Communication
- Prefers speed and directness — "Do it quickly" is default mode
- No fluff, no excessive explanations. Show results, not plans
- Understands algo trading deeply — no need to simplify concepts
- Brief confirmations after actions ("done", "fixed", "updated")

### Execution Style
- Parallel when possible — batch independent tasks
- Implement first, explain after. Don't ask permission for obvious next steps
- Surgical targeted fixes over broad rewrites
- Regression test everything — never break what already works

### Project Context
- Building an Islamic (Halal) stock analysis platform (MyTradingSpace)
- Dual-agent architecture: Fundamental Agent (v3) + Technical Agent (v2)
- Planned CWAF Orchestrator to fuse both agents
- Data sources: yfinance (backtesting), FMP (live), Musaffa (Shariah screening)
- All backtests: 12-month lookback, 60 tickers, 5 sectors
- Python 3.9.17, venv: `/Users/sirajuddeeng/Siraj-Hustle/.venv`
- Invoke: `/Users/sirajuddeeng/Siraj-Hustle/.venv/bin/python3`

### Decision-Making
- Data-driven: always cite accuracy, specificity, precision numbers
- Accepts tradeoffs explicitly (e.g., higher abstention for fewer errors)
- Root cause analysis before fixes (misclassification audit approach)
- Incremental improvement: v1 → v2 → v3 with measurable gains

---

## Prediction System — Hard Rules

> These rules govern the `predict_trade()` pipeline. Non-negotiable.

### 1. Always Route Through Orchestrator
- **NEVER** predict using only the technical agent or only the fundamental agent in isolation.
- Every prediction MUST go through the orchestrator agent, which internally runs BOTH the technical agent (12-framework scoring) AND the fundamental agent (6-evaluator scoring), then fuses them via CWAF.
- The orchestrator's `final_signal`, `final_confidence`, and `orchestrator_score` are the basis for ALL prediction decisions — not individual agent scores.

### 2. Data Lookback — No Artificial Cap
- Pull as much historical data as the Polygon API can provide. Do NOT hardcode a calendar-day lookback limit.
- The only hard requirement is ≥ 200 bars for 200-day EMA warm-up. Beyond that, more data = better pattern detection and longer-term trend context.
- If Polygon returns 2+ years of data, USE it. The agent benefits from deeper history.

### 3. Cutoff Date
- If the user provides a cutoff date: use it. All data up to (not beyond) that date.
- If the user does NOT provide a cutoff date: default to **today's date**.
- The cutoff date is the analysis boundary. No future data leakage.

### 4. Target Days — Window, Not Duration
- `target_days` is the **maximum prediction window** (valid range: > 2 and ≤ 30 trading days).
- Within that window, the system must find the optimal entry and exit points.
- If the system finds a trade setup, signal it with entry/exit dates within the window.
- If no valid setup exists within the window, return no-trade with reason.
- Target days is NOT the holding duration — it's the search window for a viable trade.

### 5. Long-Only Trade Direction
- All predictions are LONG trades only (buy low, sell high).
- If the orchestrator signals bearish or neutral → return the prediction with sentiment but no trade setup.

### 6. Prediction Output — Required Fields
Every prediction must return ALL of these:
- `trade_entry_date` — future date (next trading day after cutoff, or within window)
- `trade_exit_date` — within the target_days window
- `confidence_score` — from orchestrator (0–100)
- `sentiment` — bullish / bearish / neutral (from orchestrator's final_signal)
- `trade_entry_price` — close price as of cutoff date
- `trade_exit_price` — ATR-based target, adjusted for exhaustion
- `trade_profit_pct` — net after friction costs
- `patterns_formed` — technical patterns detected for this ticker
- `stop_loss_price` — ATR-based (entry − 1.5 × ATR)
- `exhaustion_date` — when uptrend shows signs of dying (or null)
- Full orchestrator context: tech_score, fund_score, fusion weights, conflict info

---

*Created: 2026-03-31 | Updated: 2026-04-05*
