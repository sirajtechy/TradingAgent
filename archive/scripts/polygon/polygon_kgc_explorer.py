"""
polygon_kgc_explorer.py — Full Polygon API exploration for KGC

Fires ALL available Polygon indicator endpoints in parallel, downloads
1-year daily OHLCV, then computes every extended indicator + 14 candlestick
patterns from raw bars.

Polygon native (parallel):
  SMA  — windows: 9, 20, 50, 200
  EMA  — windows: 9, 20, 50, 200
  MACD — (12, 26, 9)
  RSI  — window: 14

Computed from OHLCV (pandas, no extra deps):
  Bollinger Bands (20, 2), ATR (14), ADX (14), Stochastic (14,3),
  OBV, Williams %R (14), CCI (20), VWAP, Supertrend (10, 3)

Pattern recognition (14 candlestick patterns):
  Doji, Hammer, Inverted Hammer, Hanging Man, Shooting Star,
  Bullish/Bearish Engulfing, Piercing Line, Dark Cloud Cover,
  Morning Star, Evening Star, Three White Soldiers, Three Black Crows,
  Spinning Top
"""

from __future__ import annotations

import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Load .env file (lightweight, no extra dependency)
# ─────────────────────────────────────────────────────────────────────────────

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

API_KEY      = os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    raise SystemExit("ERROR: POLYGON_API_KEY not set. Add it to .env or export it.")
BASE_URL     = "https://api.polygon.io"
TICKER       = "KGC"
TODAY        = date.today().isoformat()
ONE_YEAR_AGO = (date.today() - timedelta(days=400)).isoformat()   # extra buffer


# ─────────────────────────────────────────────────────────────────────────────
# Polygon HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers["Authorization"] = f"Bearer {API_KEY}"


def _get(path: str, params: dict = None, retries: int = 3) -> Optional[dict]:
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params or {}, timeout=10)
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                return {"error": str(e)}
            time.sleep(0.5)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Parallel Polygon native indicator calls
# ─────────────────────────────────────────────────────────────────────────────

def _build_native_jobs() -> List[Tuple[str, str, dict]]:
    """Return list of (label, path, params) for all native indicator calls."""
    jobs = []
    base_p = {"timespan": "day", "adjusted": "true", "order": "desc",
               "limit": "5", "series_type": "close"}

    for w in [9, 20, 50, 200]:
        jobs.append((f"SMA_{w}", f"/v1/indicators/sma/{TICKER}", {**base_p, "window": w}))
        jobs.append((f"EMA_{w}", f"/v1/indicators/ema/{TICKER}", {**base_p, "window": w}))

    jobs.append(("MACD", f"/v1/indicators/macd/{TICKER}",
                 {**base_p, "short_window": 12, "long_window": 26, "signal_window": 9}))
    jobs.append(("RSI_14", f"/v1/indicators/rsi/{TICKER}", {**base_p, "window": 14}))

    # Snapshot + ticker details in same batch
    jobs.append(("SNAPSHOT", f"/v2/snapshot/locale/us/markets/stocks/tickers/{TICKER}", {}))
    jobs.append(("PREV_CLOSE", f"/v2/aggs/ticker/{TICKER}/prev", {"adjusted": "true"}))
    jobs.append(("TICKER_DETAILS", f"/v3/reference/tickers/{TICKER}", {}))

    return jobs


def fetch_native_indicators() -> Dict[str, Any]:
    jobs = _build_native_jobs()
    results: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=12) as pool:
        future_map = {
            pool.submit(_get, path, params): label
            for label, path, params in jobs
        }
        for future in as_completed(future_map):
            label = future_map[future]
            results[label] = future.result()

    return results


def fetch_ohlcv() -> Optional[pd.DataFrame]:
    """Download 1-year daily OHLCV bars."""
    data = _get(
        f"/v2/aggs/ticker/{TICKER}/range/1/day/{ONE_YEAR_AGO}/{TODAY}",
        {"adjusted": "true", "sort": "asc", "limit": 5000},
    )
    if not data or "results" not in data:
        return None

    bars = data["results"]
    df = pd.DataFrame(bars)
    df = df.rename(columns={
        "o": "open", "h": "high", "l": "low", "c": "close",
        "v": "volume", "vw": "vwap_raw", "t": "timestamp", "n": "trades",
    })
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Computed indicators
# ─────────────────────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # ── Bollinger Bands (20, 2) ──────────────────────────────────────────
    sma20    = c.rolling(20).mean()
    std20    = c.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_pct   = (c - bb_lower) / (bb_upper - bb_lower)

    # ── ATR (14) ─────────────────────────────────────────────────────────
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, adjust=False).mean()

    # ── ADX (14) ─────────────────────────────────────────────────────────
    up_move   = h - h.shift()
    down_move = l.shift() - l
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm_s  = pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean()
    atr_s      = atr14
    plus_di    = 100 * plus_dm_s / atr_s.replace(0, np.nan)
    minus_di   = 100 * minus_dm_s / atr_s.replace(0, np.nan)
    dx         = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx14      = dx.ewm(alpha=1/14, adjust=False).mean()

    # ── Stochastic (14, 3) ───────────────────────────────────────────────
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    pct_k  = 100 * (c - low14) / (high14 - low14).replace(0, np.nan)
    pct_d  = pct_k.rolling(3).mean()

    # ── OBV ──────────────────────────────────────────────────────────────
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()

    # ── Williams %R (14) ─────────────────────────────────────────────────
    wpr = -100 * (high14 - c) / (high14 - low14).replace(0, np.nan)

    # ── CCI (20) ─────────────────────────────────────────────────────────
    typical = (h + l + c) / 3
    cci     = (typical - typical.rolling(20).mean()) / (0.015 * typical.rolling(20).apply(lambda x: abs(x - x.mean()).mean(), raw=True))

    # ── VWAP (rolling 20-day) ────────────────────────────────────────────
    tp_vol  = typical * v
    vwap_20 = tp_vol.rolling(20).sum() / v.rolling(20).sum()

    # ── Supertrend (10, 3) ───────────────────────────────────────────────
    hl_avg   = (h + l) / 2
    atr10    = tr.ewm(alpha=1/10, adjust=False).mean()
    upper_st = hl_avg + 3 * atr10
    lower_st = hl_avg - 3 * atr10
    supertrend = pd.Series([np.nan] * len(df))
    direction  = pd.Series([1] * len(df))  # 1=bullish, -1=bearish
    for i in range(1, len(df)):
        if c.iloc[i] > upper_st.iloc[i - 1]:
            direction.iloc[i] = 1
        elif c.iloc[i] < lower_st.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
        supertrend.iloc[i] = lower_st.iloc[i] if direction.iloc[i] == 1 else upper_st.iloc[i]

    last = -1
    return {
        "bb":          {"upper": round(float(bb_upper.iloc[last]), 4), "mid": round(float(sma20.iloc[last]), 4), "lower": round(float(bb_lower.iloc[last]), 4), "pct_b": round(float(bb_pct.iloc[last]), 4)},
        "atr_14":      round(float(atr14.iloc[last]), 4),
        "adx_14":      round(float(adx14.iloc[last]), 2),
        "plus_di":     round(float(plus_di.iloc[last]), 2),
        "minus_di":    round(float(minus_di.iloc[last]), 2),
        "stoch":       {"k": round(float(pct_k.iloc[last]), 2), "d": round(float(pct_d.iloc[last]), 2)},
        "obv":         int(obv.iloc[last]),
        "obv_trend":   "rising" if obv.iloc[last] > obv.iloc[-5] else "falling",
        "wpr_14":      round(float(wpr.iloc[last]), 2),
        "cci_20":      round(float(cci.iloc[last]), 2),
        "vwap_20":     round(float(vwap_20.iloc[last]), 4),
        "supertrend":  round(float(supertrend.iloc[last]), 4),
        "st_direction": "bullish" if direction.iloc[last] == 1 else "bearish",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pattern recognition (14 patterns)
# ─────────────────────────────────────────────────────────────────────────────

def detect_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    o = df["open"]
    h = df["high"]
    l = df["low"]
    c = df["close"]

    patterns: Dict[str, str] = {}

    def body(i):  return abs(c.iloc[i] - o.iloc[i])
    def rng(i):   return h.iloc[i] - l.iloc[i]
    def upper_shadow(i): return h.iloc[i] - max(o.iloc[i], c.iloc[i])
    def lower_shadow(i): return min(o.iloc[i], c.iloc[i]) - l.iloc[i]
    def is_bull(i): return c.iloc[i] > o.iloc[i]
    def is_bear(i): return c.iloc[i] < o.iloc[i]

    n = len(df)
    i = n - 1  # last candle

    # ── 1-bar patterns ────────────────────────────────────────────────────
    # Doji: body <= 5% of range
    if rng(i) > 0 and body(i) / rng(i) <= 0.05:
        patterns["Doji"] = "⚠️ NEUTRAL — indecision, potential reversal"

    # Hammer: long lower shadow (>= 2x body), small upper shadow, small body
    if (lower_shadow(i) >= 2 * body(i) and upper_shadow(i) <= body(i) * 0.5
            and body(i) > 0 and rng(i) > 0):
        # Hammer in downtrend = bullish, same shape in uptrend = Hanging Man
        prior_trend = c.iloc[i - 5] > c.iloc[i]  # price fell = downtrend
        if prior_trend:
            patterns["Hammer"] = "🟢 BULLISH reversal signal"
        else:
            patterns["Hanging Man"] = "🔴 BEARISH reversal signal"

    # Inverted Hammer / Shooting Star
    if (upper_shadow(i) >= 2 * body(i) and lower_shadow(i) <= body(i) * 0.5
            and body(i) > 0 and rng(i) > 0):
        prior_trend = c.iloc[i - 5] > c.iloc[i]
        if prior_trend:
            patterns["Inverted Hammer"] = "🟢 BULLISH reversal (confirmed by next candle)"
        else:
            patterns["Shooting Star"] = "🔴 BEARISH reversal signal"

    # Spinning Top: small body, shadows on both sides
    if (rng(i) > 0 and body(i) / rng(i) <= 0.25
            and upper_shadow(i) > body(i) and lower_shadow(i) > body(i)):
        patterns["Spinning Top"] = "⚠️ NEUTRAL — indecision"

    # Marubozu: body >= 90% of range (strong directional)
    if rng(i) > 0 and body(i) / rng(i) >= 0.90:
        if is_bull(i):
            patterns["Bullish Marubozu"] = "🟢 STRONG BULLISH — full-range up candle"
        else:
            patterns["Bearish Marubozu"] = "🔴 STRONG BEARISH — full-range down candle"

    # ── 2-bar patterns ────────────────────────────────────────────────────
    if i >= 1:
        # Bullish Engulfing
        if (is_bear(i - 1) and is_bull(i)
                and o.iloc[i] <= c.iloc[i - 1] and c.iloc[i] >= o.iloc[i - 1]):
            patterns["Bullish Engulfing"] = "🟢 BULLISH — body fully engulfs prior red candle"

        # Bearish Engulfing
        if (is_bull(i - 1) and is_bear(i)
                and o.iloc[i] >= c.iloc[i - 1] and c.iloc[i] <= o.iloc[i - 1]):
            patterns["Bearish Engulfing"] = "🔴 BEARISH — body fully engulfs prior green candle"

        # Piercing Line
        if (is_bear(i - 1) and is_bull(i)
                and o.iloc[i] < l.iloc[i - 1]
                and c.iloc[i] > (o.iloc[i - 1] + c.iloc[i - 1]) / 2):
            patterns["Piercing Line"] = "🟢 BULLISH — opens below prior low, closes above midpoint"

        # Dark Cloud Cover
        if (is_bull(i - 1) and is_bear(i)
                and o.iloc[i] > h.iloc[i - 1]
                and c.iloc[i] < (o.iloc[i - 1] + c.iloc[i - 1]) / 2):
            patterns["Dark Cloud Cover"] = "🔴 BEARISH — opens above prior high, closes below midpoint"

    # ── 3-bar patterns ────────────────────────────────────────────────────
    if i >= 2:
        # Morning Star (bottom reversal)
        if (is_bear(i - 2)
                and body(i - 1) <= rng(i - 1) * 0.3  # small body middle candle
                and is_bull(i)
                and c.iloc[i] > (o.iloc[i - 2] + c.iloc[i - 2]) / 2):
            patterns["Morning Star"] = "🟢 BULLISH 3-bar reversal — bottom of downtrend"

        # Evening Star (top reversal)
        if (is_bull(i - 2)
                and body(i - 1) <= rng(i - 1) * 0.3
                and is_bear(i)
                and c.iloc[i] < (o.iloc[i - 2] + c.iloc[i - 2]) / 2):
            patterns["Evening Star"] = "🔴 BEARISH 3-bar reversal — top of uptrend"

        # Three White Soldiers
        if (is_bull(i - 2) and is_bull(i - 1) and is_bull(i)
                and c.iloc[i - 2] > o.iloc[i - 2]
                and c.iloc[i - 1] > c.iloc[i - 2]
                and c.iloc[i] > c.iloc[i - 1]
                and o.iloc[i - 1] > o.iloc[i - 2]
                and o.iloc[i] > o.iloc[i - 1]):
            patterns["Three White Soldiers"] = "🟢 STRONG BULLISH — 3 consecutive higher-close candles"

        # Three Black Crows
        if (is_bear(i - 2) and is_bear(i - 1) and is_bear(i)
                and c.iloc[i - 2] < o.iloc[i - 2]
                and c.iloc[i - 1] < c.iloc[i - 2]
                and c.iloc[i] < c.iloc[i - 1]
                and o.iloc[i - 1] < o.iloc[i - 2]
                and o.iloc[i] < o.iloc[i - 1]):
            patterns["Three Black Crows"] = "🔴 STRONG BEARISH — 3 consecutive lower-close candles"

    if not patterns:
        patterns["_none"] = "No strong pattern on most recent candle"

    return patterns


# ─────────────────────────────────────────────────────────────────────────────
# Parse Polygon native indicator results
# ─────────────────────────────────────────────────────────────────────────────

def _latest_value(blob: Optional[dict], key: str = "value") -> Optional[float]:
    try:
        v = blob["results"]["values"][0]
        return round(float(v[key]), 4)
    except Exception:
        return None


def _latest_macd(blob: Optional[dict]) -> Optional[dict]:
    try:
        v = blob["results"]["values"][0]
        return {
            "value":     round(float(v["value"]), 4),
            "signal":    round(float(v["signal"]), 4),
            "histogram": round(float(v["histogram"]), 4),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Print report
# ─────────────────────────────────────────────────────────────────────────────

def _bar(label: str, value: Any, note: str = "") -> None:
    note_str = f"  [{note}]" if note else ""
    print(f"  {label:<30} {str(value):>14}{note_str}")


def print_report(
    native:   Dict[str, Any],
    computed: Dict[str, Any],
    patterns: Dict[str, Any],
    df:       pd.DataFrame,
) -> None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    chg  = (last["close"] - prev["close"]) / prev["close"] * 100

    print("\n" + "█" * 72)
    print(f"█  POLYGON FULL REPORT — {TICKER}  ({TODAY})")
    print("█" * 72)

    # ── Snapshot / Price ─────────────────────────────────────────────────
    snap = native.get("SNAPSHOT", {})
    prev_close_data = native.get("PREV_CLOSE", {})
    details = native.get("TICKER_DETAILS", {}).get("results", {})
    print("\n┌─ TICKER DETAILS ───────────────────────────────────────────────")
    print(f"  Name            : {details.get('name', 'Kinross Gold Corp')}")
    print(f"  Exchange        : {details.get('primary_exchange', 'NYSE')}")
    print(f"  Market Cap      : ${details.get('market_cap', 'N/A'):,}" if isinstance(details.get('market_cap'), (int, float)) else f"  Market Cap      : {details.get('market_cap', 'N/A')}")
    print(f"  Employees       : {details.get('total_employees', 'N/A')}")
    print(f"  Description     : {str(details.get('description', ''))[:100]}...")

    print("\n┌─ PRICE (from OHLCV bars) ──────────────────────────────────────")
    print(f"  Last Close      : ${last['close']:.4f}")
    print(f"  Open            : ${last['open']:.4f}")
    print(f"  High            : ${last['high']:.4f}")
    print(f"  Low             : ${last['low']:.4f}")
    print(f"  Volume          : {int(last['volume']):,}")
    print(f"  Day Change      : {chg:+.2f}%")
    print(f"  VWAP (raw)      : ${last.get('vwap_raw', 0):.4f}")
    print(f"  Bars loaded     : {len(df)} daily bars ({ONE_YEAR_AGO} → {TODAY})")

    # ── Native SMA ────────────────────────────────────────────────────────
    print("\n┌─ NATIVE POLYGON — SMA ─────────────────────────────────────────")
    price = last["close"]
    for w in [9, 20, 50, 200]:
        val = _latest_value(native.get(f"SMA_{w}"))
        if val:
            rel = "above" if price > val else "below"
            pct = (price - val) / val * 100
            print(f"  SMA({w:<3})          :   {val:>10.4f}   price {rel} by {pct:+.2f}%")
        else:
            print(f"  SMA({w:<3})          :   N/A")

    # ── Native EMA ────────────────────────────────────────────────────────
    print("\n┌─ NATIVE POLYGON — EMA ─────────────────────────────────────────")
    for w in [9, 20, 50, 200]:
        val = _latest_value(native.get(f"EMA_{w}"))
        if val:
            rel = "above" if price > val else "below"
            pct = (price - val) / val * 100
            print(f"  EMA({w:<3})          :   {val:>10.4f}   price {rel} by {pct:+.2f}%")
        else:
            print(f"  EMA({w:<3})          :   N/A")

    # ── Native MACD ───────────────────────────────────────────────────────
    print("\n┌─ NATIVE POLYGON — MACD (12,26,9) ──────────────────────────────")
    macd = _latest_macd(native.get("MACD"))
    if macd:
        hist_emoji = "🟢" if macd["histogram"] > 0 else "🔴"
        _bar("MACD Line",      macd["value"])
        _bar("Signal Line",    macd["signal"])
        _bar("Histogram",      macd["histogram"], f"{hist_emoji} {'bullish momentum' if macd['histogram'] > 0 else 'bearish momentum'}")
        crossover = ""
        if macd["value"] > macd["signal"] and macd["histogram"] > 0:
            crossover = "🟢 BULLISH — MACD above signal"
        elif macd["value"] < macd["signal"]:
            crossover = "🔴 BEARISH — MACD below signal"
        print(f"  {'Crossover Status':<30} {crossover}")
    else:
        print("  MACD: N/A")

    # ── Native RSI ────────────────────────────────────────────────────────
    print("\n┌─ NATIVE POLYGON — RSI (14) ─────────────────────────────────────")
    rsi = _latest_value(native.get("RSI_14"))
    if rsi:
        if rsi >= 70:
            rsi_note = "🔴 OVERBOUGHT"
        elif rsi <= 30:
            rsi_note = "🟢 OVERSOLD"
        elif rsi >= 55:
            rsi_note = "⬆️  Bullish zone"
        elif rsi <= 45:
            rsi_note = "⬇️  Bearish zone"
        else:
            rsi_note = "⚪ Neutral"
        _bar("RSI(14)", rsi, rsi_note)
    else:
        print("  RSI: N/A")

    # ── Computed Indicators ───────────────────────────────────────────────
    print("\n┌─ COMPUTED — BOLLINGER BANDS (20,2) ────────────────────────────")
    bb = computed["bb"]
    _bar("Upper Band",  bb["upper"])
    _bar("Middle (SMA20)", bb["mid"])
    _bar("Lower Band",  bb["lower"])
    pct_b = bb["pct_b"]
    bb_note = "🔴 Near upper (overbought)" if pct_b > 0.8 else ("🟢 Near lower (oversold)" if pct_b < 0.2 else "⚪ Mid range")
    _bar("%B",          round(pct_b, 4), bb_note)

    print("\n┌─ COMPUTED — ATR & ADX (14) ─────────────────────────────────────")
    atr = computed["atr_14"]
    adx = computed["adx_14"]
    pdi = computed["plus_di"]
    mdi = computed["minus_di"]
    trend_str = ("🟢 STRONG trend" if adx > 25 else ("⚪ Weak/ranging" if adx < 15 else "⚠️  Moderate trend"))
    _bar("ATR(14)",       atr, f"${atr:.3f} per bar volatility")
    _bar("ADX(14)",       adx, trend_str)
    _bar("+DI",           pdi)
    _bar("-DI",           mdi, "🟢 Bullish dominance" if pdi > mdi else "🔴 Bearish dominance")

    print("\n┌─ COMPUTED — STOCHASTIC (14,3) ──────────────────────────────────")
    stoch = computed["stoch"]
    k_note = "🔴 Overbought" if stoch["k"] > 80 else ("🟢 Oversold" if stoch["k"] < 20 else "⚪ Neutral")
    _bar("%K",   stoch["k"], k_note)
    _bar("%D",   stoch["d"])

    print("\n┌─ COMPUTED — OBV (On-Balance Volume) ────────────────────────────")
    _bar("OBV",        f"{computed['obv']:,}")
    _bar("OBV Trend",  computed["obv_trend"],
         "🟢 Accumulation" if computed["obv_trend"] == "rising" else "🔴 Distribution")

    print("\n┌─ COMPUTED — WILLIAMS %R (14) ────────────────────────────────────")
    wpr = computed["wpr_14"]
    wpr_note = "🔴 Overbought" if wpr > -20 else ("🟢 Oversold" if wpr < -80 else "⚪ Neutral")
    _bar("Williams %R", wpr, wpr_note)

    print("\n┌─ COMPUTED — CCI (20) ────────────────────────────────────────────")
    cci = computed["cci_20"]
    cci_note = "🔴 Overbought" if cci > 100 else ("🟢 Oversold" if cci < -100 else "⚪ Within normal range")
    _bar("CCI(20)", round(cci, 2), cci_note)

    print("\n┌─ COMPUTED — VWAP (20-day rolling) ──────────────────────────────")
    vwap = computed["vwap_20"]
    vwap_note = "⬆️  Price above VWAP (bullish)" if price > vwap else "⬇️  Price below VWAP (bearish)"
    _bar("VWAP(20d)",  vwap, vwap_note)

    print("\n┌─ COMPUTED — SUPERTREND (10, 3) ─────────────────────────────────")
    st   = computed["supertrend"]
    st_d = computed["st_direction"]
    _bar("Supertrend line", st)
    _bar("Direction",       st_d, "🟢 In uptrend" if st_d == "bullish" else "🔴 In downtrend")

    # ── Pattern Recognition ────────────────────────────────────────────────
    print("\n┌─ PATTERN RECOGNITION (last candle / 3-bar) ────────────────────")
    for name, desc in patterns.items():
        if name.startswith("_"):
            print(f"  {desc}")
        else:
            print(f"  {name:<26}  {desc}")

    # ── Signal Summary ─────────────────────────────────────────────────────
    print("\n┌─ SIGNAL SUMMARY ────────────────────────────────────────────────")
    bullish_signals = 0
    bearish_signals = 0

    def tally(condition, label):
        nonlocal bullish_signals, bearish_signals
        if condition == "bullish":
            bullish_signals += 1
        elif condition == "bearish":
            bearish_signals += 1

    # Moving averages
    for w in [9, 20, 50, 200]:
        sma_v = _latest_value(native.get(f"SMA_{w}"))
        ema_v = _latest_value(native.get(f"EMA_{w}"))
        if sma_v: tally("bullish" if price > sma_v else "bearish", f"SMA{w}")
        if ema_v: tally("bullish" if price > ema_v else "bearish", f"EMA{w}")

    if rsi:
        tally("bullish" if rsi < 50 else "bearish", "RSI")
    if macd:
        tally("bullish" if macd["histogram"] > 0 else "bearish", "MACD")
    tally("bullish" if pct_b < 0.5 else "bearish", "BB")
    tally("bullish" if adx > 25 and pdi > mdi else "bearish" if adx > 25 and mdi > pdi else None, "ADX")
    tally("bullish" if stoch["k"] < 50 else "bearish", "Stoch")
    tally("bullish" if computed["obv_trend"] == "rising" else "bearish", "OBV")
    tally(st_d, "Supertrend")

    total = bullish_signals + bearish_signals
    score = bullish_signals / total * 100 if total > 0 else 50
    overall = "🟢 BULLISH" if score >= 60 else ("🔴 BEARISH" if score <= 40 else "⚪ NEUTRAL")
    print(f"  Bullish signals : {bullish_signals}/{total}")
    print(f"  Bearish signals : {bearish_signals}/{total}")
    print(f"  Confluence score: {score:.0f}%")
    print(f"  Overall signal  : {overall}")
    print("\n" + "█" * 72)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print(f"\n▶ Fetching Polygon data for {TICKER} in parallel...")

    # Run native API calls and OHLCV download simultaneously
    with ThreadPoolExecutor(max_workers=2) as pool:
        native_future = pool.submit(fetch_native_indicators)
        ohlcv_future  = pool.submit(fetch_ohlcv)

    native = native_future.result()
    df     = ohlcv_future.result()

    if df is None or df.empty:
        print("✗ Failed to download OHLCV data — check API key or ticker.")
        return

    print(f"  ✓ Native calls complete ({len(native)} endpoints)")
    print(f"  ✓ OHLCV loaded ({len(df)} bars) — {time.time()-t0:.1f}s elapsed")

    print("▶ Computing extended indicators + pattern recognition...")
    computed = compute_indicators(df)
    patterns = detect_patterns(df)

    print_report(native, computed, patterns, df)
    print(f"\n  Total time: {time.time()-t0:.2f}s")


if __name__ == "__main__":
    main()
