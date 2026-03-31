# Memory — User Context & Environment Facts

> Persistent facts about the user's setup, preferences, and workspace. Updated as things change.

## User Profile
- Name: Siraj
- OS: macOS (Apple Silicon / arm64)
- Primary workspace: `/Users/sirajuddeeng/Siraj-Hustle`

## TradingView Setup
- Premium TradingView account (active, logged in via Comet browser)
- Session cookies configured in VS Code MCP:
  - `TRADINGVIEW_SESSION_ID` and `TRADINGVIEW_SESSION_ID_SIGN` — stored in mcp.json
  - Cookies expire on logout — if MCP breaks, re-copy from browser DevTools > Application > Cookies

## MCP Servers Configured
| Server | Type | Purpose |
|---|---|---|
| `tradingview-chart-mcp` | stdio (Python/Selenium) | Chart screenshots using premium session |
| `tradingview-mcp-server` | stdio (npx) | Public screener API (no auth needed) |
| `github-mcp-server` | http | GitHub Copilot MCP |

## Key Paths
- Chart MCP repo: `/Users/sirajuddeeng/Siraj-Hustle/tradingview-chart-mcp`
- Chart MCP venv Python: `/Users/sirajuddeeng/Siraj-Hustle/tradingview-chart-mcp/.venv/bin/python3`
- Chart MCP entry: `main_optimized.py` (production, browser pooling, 4 concurrent)
- MCP config: `~/Library/Application Support/Code/User/mcp.json`
- Chromedriver: `/usr/local/bin/chromedriver` (v146, matching Chrome 146)
- Python 3.12: `/opt/homebrew/bin/python3.12`
- System Python: 3.9.6 (too old for mcp package)

## Trading Workspace
- MyTradingSpace: technical + fundamental agents, backtesting
- Technical agent v2: 54.9% acc, aggressive/bullish bias
- Fundamental agent v3: 59.3% acc, conservative
- Orchestrator: CWAF strategy (Confidence-Weighted Asymmetric Fusion)
- 20 overlapping tickers: Tech (AAPL,MSFT,NVDA,GOOGL,META,AMZN,TSLA,ORCL,ANET,CRM) + Energy (XOM,CVX,COP,SLB,OXY,PSX,VLO,MPC,EOG,HAL)

## User Preferences
- Wants fast, no-fluff responses
- Cross-checks analysis with other AIs — accuracy matters more than speed
- Expects me to self-correct and document mistakes
- Prefers both daily and weekly timeframes for stock analysis

---

*Created: 2026-03-31*
