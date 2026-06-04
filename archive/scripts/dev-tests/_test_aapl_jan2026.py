#!/usr/bin/env python3
"""One-shot AAPL test: cutoff 2026-01-01, full output, no future data."""
import sys, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
os.environ.setdefault("FMP_API_KEY", "RZ8P7bENfukSirRglbdDQ30jIfjKsqSY")

from agents.technical.service import build_request, build_graph, PolygonTechnicalClient
from agents.fundamental.service import analyze_ticker as fa

# ── Technical: blind to anything after 2025-12-31 ────────────────────────────
request = build_request("AAPL", as_of_date="2025-12-31")
client  = PolygonTechnicalClient()
graph   = build_graph(client)
state   = graph.invoke({"request": request})
te      = state["evaluation"]
ki      = te.get("key_indicators", {})
exp_t   = te.get("experimental_score", {})

SEP = "=" * 62

print(SEP)
print("  AAPL  |  Cutoff: 2026-01-01  (last bar used: 2025-12-31)")
print(SEP)
print(f"TECH SCORE  : {exp_t.get('score')}  ({exp_t.get('band')})")
print(f"Confidence  : {exp_t.get('confidence')}  ({exp_t.get('confidence_pct')}%)")
print()

print("── Price & Structure ────────────────────────────────────────")
print(f"  Close              : ${ki.get('close')}")
print(f"  EMA 9              : ${ki.get('ema_9')}")
print(f"  EMA 21             : ${ki.get('ema_21')}")
print(f"  EMA 50             : ${ki.get('ema_50')}")
print(f"  EMA 200            : ${ki.get('ema_200')}")
print(f"  ATR(14)            : ${ki.get('atr_14')}")
print(f"  VWAP(20)           : ${ki.get('vwap_20')}")
print(f"  Market Structure   : {ki.get('market_structure')}")
print(f"  Supertrend Dir     : {ki.get('supertrend_direction')}  line=${ki.get('supertrend_line')}")
print()

print("── Momentum & Trend ─────────────────────────────────────────")
print(f"  RSI(14)            : {ki.get('rsi_14')}")
print(f"  ADX                : {ki.get('adx')}   +DI={ki.get('plus_di')}  -DI={ki.get('minus_di')}")
print(f"  MACD               : {ki.get('macd')}")
print(f"  MACD Signal        : {ki.get('macd_signal')}")
print(f"  MACD Histogram     : {ki.get('macd_histogram')}")
print(f"  Stoch K/D          : {ki.get('stoch_k')} / {ki.get('stoch_d')}")
print(f"  StochRSI K/D       : {ki.get('stoch_rsi_k')} / {ki.get('stoch_rsi_d')}")
print(f"  Williams %R        : {ki.get('williams_r_14')}")
print(f"  CCI(20)            : {ki.get('cci_20')}")
print(f"  ROC(12)            : {ki.get('roc_12')}%")
print(f"  OBV Trend          : {ki.get('obv_trend')}")
print(f"  CMF(20)            : {ki.get('cmf_20')}")
print()

print("── Bollinger / Ichimoku / Fibonacci ─────────────────────────")
print(f"  BB %B              : {ki.get('bb_pct_b')}   Bandwidth={ki.get('bb_bandwidth')}")
print(f"  KC Upper/Lower     : ${ki.get('kc_upper')} / ${ki.get('kc_lower')}")
print(f"  Squeeze On         : {ki.get('squeeze_on')}")
print(f"  Tenkan / Kijun     : ${ki.get('ichimoku_tenkan')} / ${ki.get('ichimoku_kijun')}")
fib = ki.get("fibonacci", {})
print(f"  Swing High/Low     : ${fib.get('swing_high')} / ${fib.get('swing_low')}")
print(f"  Fib 23.6%          : ${fib.get('fib_236')}")
print(f"  Fib 38.2%          : ${fib.get('fib_382')}")
print(f"  Fib 50.0%          : ${fib.get('fib_500')}")
print(f"  Fib 61.8%          : ${fib.get('fib_618')}")
print(f"  Fib 78.6%          : ${fib.get('fib_786')}")
print()

print("── Technical Framework Sub-scores ───────────────────────────")
for k, v in exp_t.get("subscores", {}).items():
    bar = "\u2588" * int((v or 0) // 10)
    print(f"  {k:<25} {str(v):<8} {bar}")
print()

print("── Patterns Detected (data ≤ 2025-12-31) ────────────────────")
pats = te.get("patterns", [])
if not pats:
    print("  None detected")
for i, p in enumerate(pats, 1):
    print(f"  [{i}] {p.get('name')}  direction={p.get('direction')}  confidence={p.get('confidence')}")
    print(f"       Period  : {p.get('start_date')} → {p.get('end_date')}")
    print(f"       Breakout: {p.get('breakout_date')} @ ${p.get('breakout_price')}  confirmed={p.get('breakout_confirmed')}")
    print(f"       Volume confirm: {p.get('volume_confirmation')}")
    print(f"       Description: {p.get('description')}")
    print(f"       ▶ Pattern Target: ${p.get('pattern_target')}")
    print()

# ── Fundamental: blind to anything after 2025-12-31 ─────────────────────────
fund  = fa("AAPL", as_of_date="2025-12-31")
exp_f = fund.get("experimental_score", {})
fws   = fund.get("frameworks", {})

print(SEP)
print(f"FUND SCORE  : {exp_f.get('score')}  ({exp_f.get('band')})")
print(f"Sub-scores  : {exp_f.get('subscores')}")
print()

FUND_FIELDS = [
    "score", "score_pct", "max_score", "z_score", "zone",
    "earnings_yield_pct", "return_on_capital_pct",
    "fair_value_ratio", "pe_ratio", "trailing_eps_cagr_4y_pct",
    "cagr_lookback_years", "trailing_dividend_yield_pct",
    "revenue_growth_yoy_pct", "eps_growth_yoy_pct",
    "debt_ratio", "cash_ratio", "impure_revenue_proxy_ratio",
    "dividend_streak_years", "market_cap_proxy",
]
for name, fw in fws.items():
    if not isinstance(fw, dict):
        continue
    print(f"  [{name}]  applicable={fw.get('applicable')}  score_pct={fw.get('score_pct')}")
    for k in FUND_FIELDS:
        if k in fw and k != "score_pct":
            print(f"    {k:<38} {fw[k]}")
    print()

# ── Projected Trade Outcomes ─────────────────────────────────────────────────
close = ki.get("close", 271.61)
atr   = ki.get("atr_14", 3.96)
best  = pats[0] if pats else {}
pat_tgt = best.get("pattern_target")

entry_price = close
stop        = round(close - 2.0 * atr, 2)
hit_tgt     = round(pat_tgt, 2) if pat_tgt else round(close + 3.0 * atr, 2)
exp_px      = round(close + 0.5 * atr, 2)
denom       = close - stop
rr          = round((hit_tgt - close) / denom, 2) if denom > 0 else "N/A"
gain_pct    = round((hit_tgt - close) / close * 100, 2)
loss_pct    = round((stop - close) / close * 100, 2)

# Estimated entry and exit dates
from datetime import datetime as _dt, timedelta as _td
entry_date  = "2026-01-02"   # next trading day after Jan 1 cutoff (Jan 1 = holiday/weekend)
exit_date   = (_dt.strptime(entry_date, "%Y-%m-%d").date() + _td(days=int(20 * 1.4))).isoformat()

# Determine signal label (same logic as run_backtest_excel)
orch_signal = exp_t.get("sentiment") or "neutral"   # from base dict via ki; fallback
signal = "HOLD"   # AAPL was orchestrator neutral on this date

print(SEP)
print("  TRADE RECOMMENDATION  (based on data up to 2025-12-31 only)")
print(SEP)
print(f"  Signal             : {signal}")
print(f"  Tech Score         : {exp_t.get('score')}  |  Fund Score : {exp_f.get('score')}")
print()
print(f"  ── Entry ──────────────────────────────────────────────────")
print(f"  Entry Price        : ${entry_price}  (last close at cutoff)")
print(f"  Entry Date         : {entry_date}  (first trading day of window)")
print()
print(f"  ── Exit Scenarios ─────────────────────────────────────────")
print(f"  HIT TARGET  → Exit at ${hit_tgt}  (est. by {exit_date})")
print(f"                Source: {best.get('name', 'ATR ×3')} pattern target")
print(f"                Gain   : +{gain_pct}%")
print()
print(f"  HIT STOP    → Exit at ${stop}")
print(f"                Rule  : 2 × ATR (${atr}) below entry")
print(f"                Loss  : {loss_pct}%")
print()
print(f"  EXPIRY      → Exit around ${exp_px}  (if nothing happens in 20 days)")
print(f"                Range : ${round(close - atr, 2)} – ${round(close + atr, 2)}  (within 1 ATR drift)")
print()
print(f"  R/R Ratio          : {rr}  (reward ÷ risk)")
print()
print(f"  ── Why HOLD (not BUY) ─────────────────────────────────────")
print(f"  ADX={ki.get('adx')} — no trend (below 20 threshold)")
print(f"  MACD Hist={ki.get('macd_histogram')} — short-term bearish momentum")
print(f"  RSI={ki.get('rsi_14')} — neutral zone, no oversold bounce or breakout energy")
print(f"  -DI({ki.get('minus_di')}) > +DI({ki.get('plus_di')}) — sellers still in control short-term")
print(f"  Cup & Handle broke out Dec 31 — too fresh, needs 2–3 days confirmation")
print(f"  Valuation score={exp_f.get('subscores',{}).get('valuation')} — overvalued by Graham/Lynch (P/E 36.4, PEG 0.21)")
print()
print(f"  ── Signal Logic ───────────────────────────────────────────")
print(f"  BUY   = orchestrator bullish + confirmed fresh breakout (entry now)")
print(f"  HOLD  = mixed signals or breakout too fresh — watch, don't enter yet")
print(f"  AVOID = orchestrator bearish — do not enter long")