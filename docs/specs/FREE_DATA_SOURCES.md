# Free & Low-Cost Data Sources

This project supports paid APIs (Polygon/Massive, FMP, FRED) and **free fallbacks** when keys are missing or paid tiers fail.

## Config validation (FEAT-001)

Validate your `.env` against the platform schema before running agents:

```bash
./bin/mts config validate              # validates MyTradingSpace/.env
./bin/mts config validate --env .env.example
```

Checks:

| Env var | Allowed values |
|---------|----------------|
| `MACRO_DATA_SOURCE` | `auto`, `fred`, `yfinance` |
| `NEWS_DATA_SOURCE` | `auto`, `fmp`, `yfinance` |
| `INSIDER_DATA_SOURCE` | `auto`, `fmp`, `yfinance` |
| `GEOPOLITICS_DATA_SOURCE` | `auto`, `fmp`, `yfinance` |
| `MARKET_DATA_SOURCE` | `auto`, `polygon`, `yfinance` |
| `LLM_PROVIDER` | `deterministic`, `openai` |

Unknown keys (not in `.env.example` / platform schema) produce **errors**. Placeholder API keys produce **warnings**.

Implementation: `core/config_schema.py` · Tests: `tests/test_config_schema.py`

## Macro agent

| Source | Cost | Env | What you get |
|--------|------|-----|--------------|
| [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) | **Free** (API key) | `FRED_API_KEY` | Fed funds, CPI YoY, unemployment, T10Y2Y |
| yfinance proxy | **Free** | `MACRO_DATA_SOURCE=yfinance` | ^TNX / ^IRX yield curve proxy (no CPI/unemployment) |

Other free macro sources (manual / future): [IMF WEO](https://www.imf.org/en/Data), [World Bank Open Data](https://data.worldbank.org/), [OECD.Stat](https://stats.oecd.org/), [BIS Statistics](https://www.bis.org/statistics/) — see [TopDown Charts list](https://www.topdowncharts.com/post/2018/05/12/8-free-macro-and-market-data-sources).

Default: `MACRO_DATA_SOURCE=auto` → FRED if key set, else yfinance.

## News agent

| Source | Cost | Env | What you get |
|--------|------|-----|--------------|
| FMP | Paid | `FMP_API_KEY` | Headlines, analyst grades, price targets |
| yfinance | **Free** | `NEWS_DATA_SOURCE=yfinance` | Headlines only |

Default: `NEWS_DATA_SOURCE=auto` → FMP if key works, else yfinance.

## Market data (Phoenix, market_summary)

| Source | Cost | Env | What you get |
|--------|------|-----|--------------|
| [Polygon / Massive](https://massive.com/) | Paid | `POLYGON_API_KEY` | OHLCV, VIX (I:VIX) |
| yfinance | **Free** | `MARKET_DATA_SOURCE=yfinance` | ^VIX, SPY, sector ETFs via history |

Default: `MARKET_DATA_SOURCE=auto` → Polygon if key works, else yfinance.

### Insider (ticker-specific)

| Source | Cost | Env | What you get |
|--------|------|-----|--------------|
| **SEC EDGAR Form 4** | **Free** | `SEC_EDGAR_USER_AGENT` | Authoritative insider buys/sales from Form 4 XML |
| FMP | Paid | `FMP_API_KEY` | Aggregated insider trades |
| yfinance | **Free** | `INSIDER_DATA_SOURCE=yfinance` | Insider transactions dataframe |

Default: `INSIDER_DATA_SOURCE=auto` → SEC EDGAR Form 4, then FMP if key works, else yfinance.

## Geopolitics agent

| Source | Cost | Env | What you get |
|--------|------|-----|--------------|
| FMP general/forex news | Paid | `FMP_API_KEY` | Broad news scan |
| yfinance | **Free** | `GEOPOLITICS_DATA_SOURCE=yfinance` | SPY/QQQ/XLE/GLD/UUP news keyword scan |

Default: `GEOPOLITICS_DATA_SOURCE=auto` → FMP if key works, else yfinance.

## LLM summaries

| Mode | Env | Notes |
|------|-----|-------|
| **Deterministic digest** (default) | `LLM_PROVIDER=deterministic` | Compiles all agent bullets — no OpenAI key |
| OpenAI-compatible | `LLM_PROVIDER=openai` + `LLM_ENABLED=true` | Optional narrative |

Use Cursor chat on the `research_digest` / `agent_breakdown` JSON for human interpretation — no OpenAI key required in `./bin/mts`.

## Human decision mode (`--fusion full`)

- **All agents run** regardless of Phoenix BUY/WATCH/AVOID
- Output: `agent_breakdown` (per-agent signal, score, bullets, report, errors, native extras)
- `fusion.advisory_verdict` is reference only — **you** decide buy/hold/avoid
- No agent cards or auto-skipping — full analysis for every agent every time
