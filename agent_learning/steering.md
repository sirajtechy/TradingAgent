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

*Created: 2026-03-31 | Updated: 2026-07-11*
