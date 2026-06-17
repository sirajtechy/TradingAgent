# MyTradingSpace — One-Pager

Lean map of what we built, what came from the momentum podcast, and where to look. Halal US equities (not raw NASDAQ); sector backtests use the same 12 GICS buckets as your halal universe.

---

## From the YouTube momentum podcast → what we coded

| Podcast idea | Our module | One line |
|--------------|------------|----------|
| Cross-sectional momentum rank | `agents/portfolio/scorer.py` | Rank all universe names by multi-horizon return ÷ volatility — buy leaders, not dips. |
| Top-N equal-weight book | `agents/portfolio/selector.py` + `sizer.py` | 20 names, ~$10k each on $200k budget, sector cap 25%. |
| FRR (Find / Remove / Replace) | `agents/portfolio/rebalancer.py` | Monthly rebalance on the 21st; drop names that fall below exit rank (~top 10% of universe). |
| Regime → cash | `agents/portfolio/regime.py` | Weekly Supertrend on SPY; bear = 100% cash (no gold sleeve in v1). |
| Portfolio backtest (CAGR, DD, monthly CSV) | `agents/portfolio/simulator.py` + `./bin/mts portfolio backtest` | Sigma-Scanner-style sim; 1y pilot: +63.8% on momentum-only top10 universe. |
| Bet on the rule set, not one stock | `./bin/mts portfolio allocate` | Advisory 20-name book, not single-ticker BUY. |

**Not from podcast (ours):** Phoenix + FA daily pipeline, 8 intelligence agents, 4 trader strategies, halal gate, parallel full-agent enrich (~90s).

---

## Agents (modules)

| Layer | Agent / package | Role in one line |
|-------|-----------------|------------------|
| Production | **Phoenix** | Daily TA — stage, VCP, BUY/WATCH/AVOID. |
| Production | **Fundamental** | Shariah + FA score; fused with Phoenix (90/10 CWAF). |
| Intelligence | **Macro** | FRED regime (rates, CPI, curve). |
| Intelligence | **Market summary** | SPY, VIX, sector ETFs. |
| Intelligence | **News** | FMP headlines + analyst grades. |
| Intelligence | **Insider** | Form 4 / insider flow. |
| Intelligence | **Sentiment** | Weighted news + analyst + insider + macro + geo. |
| Intelligence | **Geopolitics** | Geo news keyword scan. |
| Strategies | **Minervini / Moglen / Breitstein / McIntosh** | Orthogonal swing experts + `blend` meta-signals. |
| Portfolio | **`agents/portfolio/`** | Momentum rank + FRR + optional multi-agent conviction book. |
| Orchestrator | **`pipeline_full` + `fusion_full`** | Runs all agents; human decision mode. |

**Default production:** `./bin/mts daily` = Phoenix + FA only. Portfolio + full fusion are opt-in.

---

## Scoring (two modes)

**A — Per-ticker (daily / analyze)**  
Phoenix score + FA → CWAF fusion → optional `--strategy-profile blend` → optional `--fusion full` (8 agents).

**B — Portfolio book (allocate / backtest)**  
```
conviction ≈ 25% momentum rank + 20% Phoenix fusion + 20% strategy blend
           + 15% intelligence consensus + 10% RS vs SPY + 10% smoothness
```
Momentum core: `(1M + 6M + 9M return) / 3M volatility`. With `--full-agents`, top 10 names get real agent scores; ranks 11–20 stay momentum-only unless you raise `--enrich-max`.

Config: `data/config/portfolio_rules.json`.

---

## Dashboard today (`http://localhost:3055`)

| Route | Shows |
|-------|--------|
| `/research/portfolio` | **Allocation book** (rank, conviction, Phoenix/intel/strategy subscores, Enriched vs Momentum-only) + **backtest KPIs** (CAGR, DD, monthly table). |
| `/research/phoenix` | Sector pilot BUY/WATCH board (`master_pilot.json`). |
| `/research/signals` | Reconciled BUY/WATCH export. |
| `/research/runs` | Historical run bundles. |

Start: `./bin/mts dashboard -b` · Full per-ticker agent markdown: `./bin/mts analyze --ticker X --fusion full --export-breakdown`.

---

## Sector backtesting (your next focus)

Universe: **12 halal sectors** (~1,236 names), same sectors as NASDAQ-style GICS — `data/halal_universe/halal_sector_tickers.json`.

| Goal | Command |
|------|---------|
| One sector, Phoenix+FA | `./bin/mts sector --sector "Information Technology" --date YYYY-MM-DD` |
| All sectors | `./bin/mts unified --date YYYY-MM-DD` or `./bin/mts daily` |
| Portfolio momentum by sector themes | `./bin/mts portfolio backtest --start … --end … --universe top10` → see `sector_themes` in `summary.json` |
| Full sector list | Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities (+ filter N/A junk) |

**Lean rule:** use `sector` / `unified` for signal quality per sector; use `portfolio backtest` for rotation/P&L by sector theme.

---

## Key outputs

| Artifact | Path |
|----------|------|
| Allocation book | `data/output/portfolio_allocations/holdings_<date>.json` |
| Portfolio backtest | `data/output/portfolio_backtests/<run_id>/summary.json` |
| Daily signals | `data/output/trading_runs/unified_master_<date>/master_pilot.json` |
| Spec (portfolio) | `docs/specs/PORTFOLIO_ENGINE.md` |
| Commands | `Trading-Journals/DailyCommands.md` |

---

## Still lean / not built (keep scope small)

- Full-agent replay on every monthly rebalance (12× enrich) — run overnight if needed.  
- Web-research tier, API cache, `./bin/mts risk` — planned, not shipped.  
- In-dashboard markdown agent breakdown — use `analyze --export-breakdown` per ticker.  
- Raw NASDAQ-only universe — we use **halal-filtered** US list; sector labels match NASDAQ GICS.

Branch: `feature/portfolio-intelligence`.

---

## Completed

| Area | Done |
|------|------|
| **Production pipeline** | `./bin/mts daily` — Phoenix + FA on halal universe; `master_pilot.json`, BUY export, Telegram. |
| **8 intelligence agents** | Macro, market summary, news, insider, sentiment, geopolitics — standalone + `--fusion full`. |
| **4 trader strategies** | Minervini, Moglen, Breitstein, McIntosh + `blend`; `./bin/mts strategy`. |
| **Portfolio engine** | Momentum rank, FRR, regime cash, backtest + allocate; parallel `--full-agents` (~90s). |
| **Sector Phoenix+FA backtest** | `./bin/mts sector` / `unified` → per-sector `confusion_matrix.json` (TP/FP/TN/FN, precision, recall). |
| **Dashboard** | `/research/portfolio` (allocation book + backtest KPIs), phoenix, signals, runs. |
| **Docs / config** | `portfolio_rules.json`, `PORTFOLIO_ENGINE.md`, `DailyCommands.md`, this one-pager. |
| **1y portfolio pilot** | Momentum backtest Jun 2025–Jun 2026: +63.8% CAGR on top10 halal universe. |

---

## Not completed

| Area | Gap |
|------|-----|
| **Production merge** | On branch `feature/portfolio-intelligence` — not merged / no release tag. |
| **Full-agent portfolio backtest** | Historical 12-month replay with all agents each rebalance — not run. |
| **Sector confusion matrix dashboard** | Matrix exists in JSON per sector run — **not** on `/research/portfolio` yet. |
| **Portfolio × sector matrix** | No per-sector Phoenix precision table inside portfolio backtest UI. |
| **Strategy blend in enrich** | `strategy_blend_score` often 50 / empty meta — wiring incomplete. |
| **Universe hygiene** | N/A-sector junk tickers (e.g. SMJF) not filtered. |
| **Data legitimacy audit** | No automated freshness/coverage report per agent per sector. |
| **Web research / API cache / risk** | AI Research plan phases — not shipped. |
| **Intraday / swing hold backtest** | 1h/4h bars, 2–5 day exits — not wired. |
| **In-dashboard agent markdown** | Breakdown files not rendered in UI. |
| **Curated ticker watchlist flow** | No dedicated “user tickers → deep dive pack” command yet. |

---

## To-do (productionize → sector backtests → ticker deep dive)

| # | Task | One line |
|---|------|----------|
| 1 | **Run all 12 sectors** | Loop `./bin/mts sector --sector "…" --date YYYY-MM-DD` (or `unified`) → collect `confusion_matrix.json` per sector. |
| 2 | **Sector confusion scorecard** | Build table: sector × precision/recall/F1/accuracy from each run; pick sectors above threshold for live book. |
| 3 | **Dashboard sector matrix** | Add `/research/sectors` or extend phoenix page with per-sector confusion from latest `unified_master_*`. |
| 4 | **Portfolio sector mode** | `./bin/mts portfolio backtest --sector "Information Technology"` — isolate rotation P&L one sector at a time. |
| 5 | **Curated ticker pack** | `./bin/mts analyze --ticker X --fusion full --strategy-profile blend --export-breakdown` for your watchlist; batch script. |
| 6 | **Data legitimacy pass** | Per agent: log source used, bar date, API errors; flag yfinance fallback vs Polygon/FMP in output. |
| 7 | **Fix strategy enrich** | Populate `blend_score` + meta in portfolio enrich path. |
| 8 | **Filter halal universe** | Drop N/A sector + min price/volume before rank. |
| 9 | **Merge + smoke** | Merge branch; `./bin/mts daily` + one sector + one portfolio backtest in CI. |
| 10 | **Optional overnight** | Full-agent portfolio backtest 1y with `--enrich-max 10`. |

**Your workflow (realistic order):** sector backtests + confusion matrices → pick strong sectors → portfolio backtest those sectors → deep dive only on names you share via `--fusion full`.

---

## Confusion matrix — what you get today (sector basis)

| Command | Output | Metrics |
|---------|--------|---------|
| `./bin/mts sector --sector "Energy" --date 2026-06-13` | `data/output/trading_runs/<sector>_<date>/confusion_matrix.json` | TP, FP, TN, FN, accuracy, precision, recall, F1, abstention |
| `./bin/mts unified --date …` | `unified_master_<date>/` — matrix **per sector** in `master_pilot.json` → `matrices` | Same, aggregated by sector |
| `./bin/mts portfolio backtest …` | `summary.json` → `sector_themes` | **Rotation flow only** — not Phoenix BUY precision |

**Label rule (Phoenix+FA pilot):** bullish BUY/WATCH vs forward target-hit in eval window (~15 days) — see `run_halal_sector_month_pilot.py`.

---

## External data sources (by agent)

| Agent | Primary source | Fallback | Env / config | Legitimacy notes |
|-------|----------------|----------|--------------|------------------|
| **Phoenix (TA)** | [Polygon](https://polygon.io) daily OHLCV | yfinance | `POLYGON_API_KEY`, `MARKET_DATA_SOURCE` | Polygon = production; yfinance = emergency, less PIT-clean. |
| **Fundamental** | [FMP](https://financialmodelingprep.com) fundamentals | yfinance | `FMP_API_KEY`, `--fund-data-source` | FMP filing dates; yfinance approximates fiscal dates. |
| **Shariah / halal gate** | Static Musaffa JSON | — | `data/halal_universe/*.json` | Point-in-time survivorship not perfect — manual refresh. |
| **Macro** | [FRED](https://fred.stlouisfed.org) | yfinance (^TNX/^IRX proxy) | `FRED_API_KEY`, `MACRO_DATA_SOURCE` | FRED = authoritative; yfinance macro is thin. |
| **Market summary** | Polygon (SPY, sector ETFs, VIX) | yfinance | `POLYGON_API_KEY` | Same as Phoenix OHLCV path. |
| **News** | FMP news + analyst grades/targets | yfinance headlines | `FMP_API_KEY`, `NEWS_DATA_SOURCE` | Analyst data FMP-only; yfinance = headlines only. |
| **Insider** | FMP Form 4–style trades | yfinance insider df | `FMP_API_KEY`, `INSIDER_DATA_SOURCE` | SEC EDGAR is source of truth — FMP aggregated. |
| **Sentiment** | **Derived** — no own API | — | Aggregates news, insider, macro, geo, optional Polygon OHLCV | Legitimacy = only as good as upstream agents. |
| **Geopolitics** | FMP general/forex news | yfinance ETF news keywords | `FMP_API_KEY`, `GEOPOLITICS_DATA_SOURCE` | Keyword scan — qualitative, not PIT backtest-safe for live research tier. |
| **Strategies (4)** | Phoenix bars (Polygon/yfinance) + SPY | — | Same as Phoenix | Deterministic rules on same OHLCV. |
| **Portfolio momentum** | Polygon batch OHLCV | — | `POLYGON_API_KEY` | Cross-sectional rank; no FMP in core path. |
| **Portfolio regime** | Polygon weekly SPY | — | `POLYGON_API_KEY` | Supertrend on index. |
| **LLM bullets** | Deterministic digest (default) | OpenAI optional | `LLM_PROVIDER`, `OPENAI_API_KEY` | Does not change scores. |

**Validate keys before runs:** `./bin/mts config validate` · Detail: `docs/specs/FREE_DATA_SOURCES.md`.

**Not wired yet:** Finnhub, Alpaca intraday, web search/scrape, SEC EDGAR direct — listed in AI Research plan only.

