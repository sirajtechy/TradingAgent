# Intelligence Data Plan — News, Geopolitics, Sentiment, Insider

Action plan for replacing fallback data with legitimate primary sources. Status as of 2026-06-14.

## Current state (what you see in Deep Analyze)

| Agent | Primary (intended) | What runs today | Why fallback |
|-------|-------------------|-----------------|--------------|
| **Macro** | FRED | FRED ✅ (after `--refresh-context`) | Stale `context_<date>.json` cache |
| **Market summary** | Polygon OHLCV + FRED macro | Polygon SPY/sectors + yfinance VIX ✅ | Polygon `I:VIX` 403 on free tier |
| **News** | FMP headlines + grades | yfinance headlines (6–10) | FMP `/news/stock` returns **402 Payment Required** |
| **Insider** | SEC EDGAR Form 4 | yfinance insider df | **Implemented** — `sec:form4` primary; set `SEC_EDGAR_USER_AGENT` |
| **Geopolitics** | FMP general/forex news | yfinance ETF news scan | FMP 402; keyword filter often yields 0 matches |
| **Sentiment** | Derived (no own API) | Aggregates upstream agents | Shows "fallback" when news/insider use yfinance |

**Sentiment is not a data fallback** — it is a composite score. The dashboard now labels it **Derived**.

---

## Phase 1 — Done in this branch

1. **BUY/WATCH watchlist UI** — `/research/analyze/watchlist` lists all Phoenix BUY/WATCH from `master_pilot.json` with the same per-ticker deep-dive panel.
2. **Batch CLI** — `./bin/mts analyze --watchlist --fusion full --export-breakdown --refresh-context`
3. **Top 10 headlines** in news agent output + dashboard Headlines section.
4. **Geopolitics yfinance** — shows general market headlines when geo keywords do not match (context mode).
5. **Finnhub optional** — set `FINNHUB_API_KEY` for company news before yfinance (free tier: 60 calls/min).
6. **FRED** — `FRED_API_KEY` in `.env`; always pass `--refresh-context` once after key changes.

---

## Phase 2 — Recommended sources (legitimate + cost)

### News (ticker-specific, target: 10 headlines + analyst actions)

| Source | Cost | Env var | Endpoints | Notes |
|--------|------|---------|-----------|-------|
| **Finnhub** | Free tier | `FINNHUB_API_KEY` | `/company-news` | ✅ wired; good for US tickers |
| **FMP Starter+** | ~$30/mo | `FMP_API_KEY` | `/news/stock`, `/grades` | Required for analyst grades currently blocked (402) |
| **Alpha Vantage** | Free (25 req/day) | `ALPHAVANTAGE_API_KEY` | `NEWS_SENTIMENT` | Good backup; rate limited |
| **Polygon/Benzinga** | Paid add-on | `POLYGON_API_KEY` | `/v2/reference/news` | Check Massive plan includes news |
| **SEC EDGAR RSS** | Free | — | Company filings RSS | Filings not headlines; useful for material events |
| **yfinance** | Free | — | `Ticker.news` | Current fallback; 6–10 headlines, no grades |

**Recommendation:** Add `FINNHUB_API_KEY` immediately (free). Upgrade FMP tier OR add Alpha Vantage for analyst grades. Keep yfinance as last resort.

### Geopolitics (session-level, target: 10 geo-relevant headlines)

| Source | Cost | Notes |
|--------|------|-------|
| **FMP general/forex news** | Paid | Broad scan; blocked today (402) |
| **Finnhub `/news?category=general`** | Free | Wire in Phase 2b |
| **GDELT DOC 2.0 API** | Free | Keyword search; heavier integration |
| **yfinance ETF scan** | Free | ✅ improved with context headlines |

### Insider (ticker-specific) — ✅ SEC EDGAR wired

| Source | Cost | Status |
|--------|------|--------|
| **SEC EDGAR Form 4** | Free | **Primary** — parses submissions + Form 4 XML |
| FMP insider trading | Paid | Fallback if EDGAR empty / 402 |
| yfinance | Free | Last resort |
| Finnhub insider | Free tier | Optional future add-on |

### Sentiment (derived — no direct feed)

Improve by fixing upstream agents:

- News → Finnhub/FMP grades
- Insider → Finnhub insider or SEC
- Macro → FRED (done)
- Geopolitics → Finnhub general news

Sentiment quality = weighted composite of upstream scores (see `agents/sentiment/rules.py`).

---

## Phase 2b — Implementation backlog (ordered)

1. **`FINNHUB_API_KEY`** in `.env` — instant news upgrade for watchlist batch.
2. **Finnhub geopolitics client** — `/news?category=general` + keyword filter.
3. **Finnhub insider** — replace yfinance insider when key present.
4. **Alpha Vantage news** — optional third fallback with daily quota guard.
5. **SEC EDGAR insider parser** — free Form 4 for halal universe names.
6. **Dashboard sector view** — aggregate BUY/WATCH by sector with roll-up one-liners (Phase 3).
7. **Auto-refresh context** when `.env` keys change (invalidate `data/output/context/`).

---

## Commands (BUY/WATCH workflow)

```bash
# 1. Daily signals
./bin/mts daily --date YYYY-MM-DD

# 2. Batch deep analyze all BUY/WATCH (skips cached)
./bin/mts analyze --watchlist --date YYYY-MM-DD --fusion full --export-breakdown --refresh-context

# 3. Trade-focus only (BUY + WATCH score > 60)
./bin/mts analyze --watchlist --trade-focus --fusion full --export-breakdown --refresh-context

# 4. Dashboard
./bin/mts dashboard -b
# → Research Lab → BUY/WATCH dive
```

---

## Env checklist

```bash
FRED_API_KEY=...          # macro (free)
POLYGON_API_KEY=...       # Phoenix, market_summary OHLCV
FMP_API_KEY=...           # news grades, insider, geo (paid tier for news)
FINNHUB_API_KEY=...       # news + insider + geo (free tier) — ADD THIS NEXT
# ALPHAVANTAGE_API_KEY=   # optional news backup
```

Validate: `./bin/mts config validate`
