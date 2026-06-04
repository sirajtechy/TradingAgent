#!/usr/bin/env python3
"""AVGO backtest — cutoff 2026-03-31. Prints full trade breakdown."""
import sys, os
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
os.environ.setdefault("FMP_API_KEY", "RZ8P7bENfukSirRglbdDQ30jIfjKsqSY")

from agents.technical.service import build_request, build_graph, PolygonTechnicalClient, predict_trade
from scripts.run_backtest_excel import _predict_one, OUTPUT_BASE

TICKER = "AVGO"
CUTOFF = "2026-03-31"
SEP    = "=" * 62

# ── Technical ────────────────────────────────────────────────────────────────
request = build_request(TICKER, as_of_date=CUTOFF)
client  = PolygonTechnicalClient()
graph   = build_graph(client)
state   = graph.invoke({"request": request})
te      = state["evaluation"]
ki      = te.get("key_indicators", {})
exp_t   = te.get("experimental_score", {})
pats    = te.get("patterns", [])

# ── Orchestrator (runs both TA + FA internally via CWAF) ─────────────────────
result    = predict_trade(ticker=TICKER, cutoff_date=CUTOFF, target_days=20)
trade     = result.get("trade")
tech_sc   = result.get("tech_score", exp_t.get("score", "N/A"))
fund_sc   = result.get("fund_score", "N/A")

# ── Trade levels ─────────────────────────────────────────────────────────────
close = ki.get("close", 0)
atr   = ki.get("atr_14", 0)
best  = pats[0] if pats else {}
pat_tgt = best.get("pattern_target")

entry_price = close
stop        = round(close - 2.0 * atr, 2)
hit_tgt     = round(float(pat_tgt), 2) if pat_tgt else round(close + 3.0 * atr, 2)
exp_px      = round(close + 0.5 * atr, 2)
denom       = close - stop
rr          = round((hit_tgt - close) / denom, 2) if denom > 0 else "N/A"
gain_pct    = round((hit_tgt - close) / close * 100, 2) if close else "N/A"
loss_pct    = round((stop - close) / close * 100, 2) if close else "N/A"

orch_signal = result.get("sentiment", "neutral")
if trade:
    signal_label = "BUY"
elif orch_signal == "bearish":
    signal_label = "AVOID"
else:
    signal_label = "HOLD"

# ── Print ─────────────────────────────────────────────────────────────────────
print(SEP)
print(f"  {TICKER} (Broadcom)  |  Cutoff: {CUTOFF}")
print(SEP)
print(f"  Signal             : {signal_label}")
print(f"  Tech Score         : {tech_sc}  ({exp_t.get('band')})")
print(f"  Fund Score         : {fund_sc}")
print(f"  Confidence         : {result.get('confidence_score')}%")
print()
print(f"  ── Entry ──────────────────────────────────────────────────")
print(f"  Entry Price        : ${entry_price}  (last close at cutoff)")
print(f"  Entry Date         : 2026-04-01  (next trading day)")
print()
print(f"  ── Exit Scenarios ─────────────────────────────────────────")
print(f"  HIT TARGET  → Exit at  ${hit_tgt}")
src = best.get('name', 'ATR ×3') if best else 'ATR ×3'
print(f"                Source : {src}")
print(f"                Gain   : +{gain_pct}%")
print()
print(f"  HIT STOP    → Exit at  ${stop}")
print(f"                Rule   : 2 × ATR (${atr}) below entry")
print(f"                Loss   : {loss_pct}%")
print()
print(f"  EXPIRY      → Around  ${exp_px}  (20 trading days, no breakout)")
print(f"                Range  : ${round(close - atr,2)} – ${round(close + atr,2)}")
print()
print(f"  R/R Ratio          : {rr}")
print()
print(f"  ── Key Indicators ─────────────────────────────────────────")
print(f"  Close              : ${close}")
print(f"  ATR(14)            : ${atr}")
print(f"  RSI(14)            : {ki.get('rsi_14')}")
print(f"  ADX                : {ki.get('adx')}   +DI={ki.get('plus_di')}  -DI={ki.get('minus_di')}")
print(f"  MACD               : {ki.get('macd')}  Histogram={ki.get('macd_histogram')}")
print(f"  EMA 9/21/50/200    : {ki.get('ema_9')} / {ki.get('ema_21')} / {ki.get('ema_50')} / {ki.get('ema_200')}")
print(f"  Market Structure   : {ki.get('market_structure')}")
print(f"  Supertrend Dir     : {ki.get('supertrend_direction')}  (line={ki.get('supertrend_line')})")
print(f"  BB %B              : {ki.get('bb_pct_b')}   OBV Trend={ki.get('obv_trend')}")
print()
print(f"  ── Technical Framework Subscores ──────────────────────────")
for k, v in exp_t.get("subscores", {}).items():
    bar = "█" * int((v or 0) // 10)
    print(f"  {k:<25} {str(v):<8} {bar}")
print()
print(f"  ── Framework Scores ───────────────────────────────────────")
print(f"  (Fundamental API unavailable for AVGO — orchestrator used cached score)")
print()
print(f"  ── Top Patterns Detected ──────────────────────────────────")
if not pats:
    print("  None detected")
for i, p in enumerate(pats[:6], 1):
    print(f"  [{i}] {p.get('name')}  conf={p.get('confidence')}  "
          f"target=${p.get('pattern_target')}  breakout={p.get('breakout_date')}")
print()
print(f"  ── Why {signal_label} ──────────────────────────────────────────────")
print(f"  Orchestrator: {orch_signal}  (score={result.get('confidence_score')})")
print(f"  Reason: {result.get('no_trade_reason', 'Trade taken — see above')}")

# ── Write to Excel (upsert) ───────────────────────────────────────────────────
print()
out_dir    = OUTPUT_BASE / CUTOFF
out_dir.mkdir(parents=True, exist_ok=True)
excel_path = out_dir / f"{CUTOFF}.xlsx"
log_path   = out_dir / "run_log.txt"
status = _predict_one(TICKER, "Information Technology", CUTOFF, 20, excel_path, log_path)
print(SEP)
print(f"  Excel row written: {status}")
print(f"  File: {excel_path}")
