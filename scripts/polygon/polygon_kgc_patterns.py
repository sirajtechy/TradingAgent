"""
polygon_kgc_patterns.py — Comprehensive pattern recognition for KGC
                          across DAILY and WEEKLY timeframes.

Candlestick patterns (22):
  Doji, Hammer, Inverted Hammer, Hanging Man, Shooting Star,
  Bullish/Bearish Engulfing, Piercing Line, Dark Cloud Cover,
  Morning Star, Evening Star, Three White Soldiers, Three Black Crows,
  Spinning Top, Marubozu, Bullish/Bearish Harami, Tweezer Top/Bottom,
  Belt Hold Bullish/Bearish, Three Inside Up/Down

Chart patterns (10):
  Double Top, Double Bottom, Head & Shoulders, Inverse H&S,
  Ascending Triangle, Descending Triangle, Symmetrical Triangle,
  Bull Flag, Bear Flag, Rising Wedge, Falling Wedge, Channel Up/Down

Scans last 10 candles for candlestick patterns (not just last one).
Uses Polygon OHLCV bars — daily & weekly.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
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
TWO_YEARS    = (date.today() - timedelta(days=730)).isoformat()

SESSION = requests.Session()
SESSION.headers["Authorization"] = f"Bearer {API_KEY}"

SCAN_WINDOW = 10  # scan last N candles for candlestick patterns


def _get(path: str, params: dict = None, retries: int = 3) -> Optional[dict]:
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params or {}, timeout=15)
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
# Data download
# ─────────────────────────────────────────────────────────────────────────────

def fetch_bars(timespan: str) -> Optional[pd.DataFrame]:
    """Download bars from Polygon. timespan = 'day' or 'week'."""
    data = _get(
        f"/v2/aggs/ticker/{TICKER}/range/1/{timespan}/{TWO_YEARS}/{TODAY}",
        {"adjusted": "true", "sort": "asc", "limit": 5000},
    )
    if not data or "results" not in data:
        return None
    df = pd.DataFrame(data["results"])
    df = df.rename(columns={
        "o": "open", "h": "high", "l": "low", "c": "close",
        "v": "volume", "vw": "vwap_raw", "t": "timestamp",
    })
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Candlestick pattern helpers
# ─────────────────────────────────────────────────────────────────────────────

def _body(o, c):         return abs(c - o)
def _rng(h, l):          return h - l
def _upper_shad(o, h, c): return h - max(o, c)
def _lower_shad(o, l, c): return min(o, c) - l
def _is_bull(o, c):      return c > o
def _is_bear(o, c):      return c < o


def detect_candlestick_patterns(df: pd.DataFrame, window: int = SCAN_WINDOW) -> List[Dict[str, Any]]:
    """Scan last `window` candles for all candlestick patterns. Returns list of hits."""
    hits: List[Dict[str, Any]] = []
    n = len(df)
    start = max(3, n - window)  # need at least 3 prior candles for context

    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values

    for i in range(start, n):
        dt = str(df["date"].iloc[i])
        bd = _body(o[i], c[i])
        rn = _rng(h[i], l[i])
        us = _upper_shad(o[i], h[i], c[i])
        ls = _lower_shad(o[i], l[i], c[i])

        if rn == 0:
            continue

        # ---- 1-bar patterns ------------------------------------------------

        # Doji
        if bd / rn <= 0.05:
            hits.append({"date": dt, "pattern": "Doji", "signal": "neutral",
                         "desc": "Indecision — potential reversal"})

        # Spinning Top
        if bd / rn <= 0.25 and us > bd and ls > bd:
            hits.append({"date": dt, "pattern": "Spinning Top", "signal": "neutral",
                         "desc": "Indecision with shadows on both sides"})

        # Marubozu
        if bd / rn >= 0.90:
            if _is_bull(o[i], c[i]):
                hits.append({"date": dt, "pattern": "Bullish Marubozu", "signal": "bullish",
                             "desc": "Full-range up candle — strong buying"})
            else:
                hits.append({"date": dt, "pattern": "Bearish Marubozu", "signal": "bearish",
                             "desc": "Full-range down candle — strong selling"})

        # Hammer / Hanging Man
        if bd > 0 and ls >= 2 * bd and us <= bd * 0.5:
            prior_trend = c[max(0, i-5)] > c[i]  # was price higher 5 bars ago?
            if prior_trend:
                hits.append({"date": dt, "pattern": "Hammer", "signal": "bullish",
                             "desc": "Bullish reversal — long lower shadow in downtrend"})
            else:
                hits.append({"date": dt, "pattern": "Hanging Man", "signal": "bearish",
                             "desc": "Bearish reversal — long lower shadow in uptrend"})

        # Inverted Hammer / Shooting Star
        if bd > 0 and us >= 2 * bd and ls <= bd * 0.5:
            prior_trend = c[max(0, i-5)] > c[i]
            if prior_trend:
                hits.append({"date": dt, "pattern": "Inverted Hammer", "signal": "bullish",
                             "desc": "Bullish reversal — long upper shadow in downtrend"})
            else:
                hits.append({"date": dt, "pattern": "Shooting Star", "signal": "bearish",
                             "desc": "Bearish reversal — long upper shadow in uptrend"})

        # Belt Hold Bullish
        if _is_bull(o[i], c[i]) and bd / rn >= 0.70 and ls / rn <= 0.05:
            hits.append({"date": dt, "pattern": "Belt Hold Bullish", "signal": "bullish",
                         "desc": "Opens at low, closes near high — strong buying"})

        # Belt Hold Bearish
        if _is_bear(o[i], c[i]) and bd / rn >= 0.70 and us / rn <= 0.05:
            hits.append({"date": dt, "pattern": "Belt Hold Bearish", "signal": "bearish",
                         "desc": "Opens at high, closes near low — strong selling"})

        # ---- 2-bar patterns ------------------------------------------------
        if i < 1:
            continue

        bd_prev = _body(o[i-1], c[i-1])
        rn_prev = _rng(h[i-1], l[i-1])

        # Bullish Engulfing
        if (_is_bear(o[i-1], c[i-1]) and _is_bull(o[i], c[i])
                and o[i] <= c[i-1] and c[i] >= o[i-1]):
            hits.append({"date": dt, "pattern": "Bullish Engulfing", "signal": "bullish",
                         "desc": "Green candle fully engulfs prior red candle"})

        # Bearish Engulfing
        if (_is_bull(o[i-1], c[i-1]) and _is_bear(o[i], c[i])
                and o[i] >= c[i-1] and c[i] <= o[i-1]):
            hits.append({"date": dt, "pattern": "Bearish Engulfing", "signal": "bearish",
                         "desc": "Red candle fully engulfs prior green candle"})

        # Piercing Line
        if (_is_bear(o[i-1], c[i-1]) and _is_bull(o[i], c[i])
                and o[i] < l[i-1]
                and c[i] > (o[i-1] + c[i-1]) / 2):
            hits.append({"date": dt, "pattern": "Piercing Line", "signal": "bullish",
                         "desc": "Opens below prior low, closes above prior midpoint"})

        # Dark Cloud Cover
        if (_is_bull(o[i-1], c[i-1]) and _is_bear(o[i], c[i])
                and o[i] > h[i-1]
                and c[i] < (o[i-1] + c[i-1]) / 2):
            hits.append({"date": dt, "pattern": "Dark Cloud Cover", "signal": "bearish",
                         "desc": "Opens above prior high, closes below prior midpoint"})

        # Bullish Harami
        if (_is_bear(o[i-1], c[i-1]) and _is_bull(o[i], c[i])
                and o[i] > c[i-1] and c[i] < o[i-1]
                and bd < bd_prev):
            hits.append({"date": dt, "pattern": "Bullish Harami", "signal": "bullish",
                         "desc": "Small green body inside prior large red body"})

        # Bearish Harami
        if (_is_bull(o[i-1], c[i-1]) and _is_bear(o[i], c[i])
                and o[i] < c[i-1] and c[i] > o[i-1]
                and bd < bd_prev):
            hits.append({"date": dt, "pattern": "Bearish Harami", "signal": "bearish",
                         "desc": "Small red body inside prior large green body"})

        # Tweezer Top
        if (abs(h[i] - h[i-1]) / rn <= 0.02
                and _is_bull(o[i-1], c[i-1]) and _is_bear(o[i], c[i])):
            hits.append({"date": dt, "pattern": "Tweezer Top", "signal": "bearish",
                         "desc": "Equal highs — bull then bear, resistance exhaustion"})

        # Tweezer Bottom
        if (abs(l[i] - l[i-1]) / rn <= 0.02
                and _is_bear(o[i-1], c[i-1]) and _is_bull(o[i], c[i])):
            hits.append({"date": dt, "pattern": "Tweezer Bottom", "signal": "bullish",
                         "desc": "Equal lows — bear then bull, support holding"})

        # ---- 3-bar patterns ------------------------------------------------
        if i < 2:
            continue

        # Morning Star
        if (_is_bear(o[i-2], c[i-2])
                and rn_prev > 0 and bd_prev / rn_prev <= 0.30
                and _is_bull(o[i], c[i])
                and c[i] > (o[i-2] + c[i-2]) / 2):
            hits.append({"date": dt, "pattern": "Morning Star", "signal": "bullish",
                         "desc": "3-bar bottom reversal — bearish, small-body, bullish"})

        # Evening Star
        if (_is_bull(o[i-2], c[i-2])
                and rn_prev > 0 and bd_prev / rn_prev <= 0.30
                and _is_bear(o[i], c[i])
                and c[i] < (o[i-2] + c[i-2]) / 2):
            hits.append({"date": dt, "pattern": "Evening Star", "signal": "bearish",
                         "desc": "3-bar top reversal — bullish, small-body, bearish"})

        # Three White Soldiers
        if (all(_is_bull(o[j], c[j]) for j in [i-2, i-1, i])
                and c[i-1] > c[i-2] and c[i] > c[i-1]
                and o[i-1] > o[i-2] and o[i] > o[i-1]):
            hits.append({"date": dt, "pattern": "Three White Soldiers", "signal": "bullish",
                         "desc": "3 consecutive higher-close green candles"})

        # Three Black Crows
        if (all(_is_bear(o[j], c[j]) for j in [i-2, i-1, i])
                and c[i-1] < c[i-2] and c[i] < c[i-1]
                and o[i-1] < o[i-2] and o[i] < o[i-1]):
            hits.append({"date": dt, "pattern": "Three Black Crows", "signal": "bearish",
                         "desc": "3 consecutive lower-close red candles"})

        # Three Inside Up (Bullish Harami + confirmation)
        if (_is_bear(o[i-2], c[i-2])
                and _is_bull(o[i-1], c[i-1])
                and o[i-1] > c[i-2] and c[i-1] < o[i-2]
                and _is_bull(o[i], c[i])
                and c[i] > o[i-2]):
            hits.append({"date": dt, "pattern": "Three Inside Up", "signal": "bullish",
                         "desc": "Bullish harami confirmed by third higher close"})

        # Three Inside Down (Bearish Harami + confirmation)
        if (_is_bull(o[i-2], c[i-2])
                and _is_bear(o[i-1], c[i-1])
                and o[i-1] < c[i-2] and c[i-1] > o[i-2]
                and _is_bear(o[i], c[i])
                and c[i] < o[i-2]):
            hits.append({"date": dt, "pattern": "Three Inside Down", "signal": "bearish",
                         "desc": "Bearish harami confirmed by third lower close"})

    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Chart pattern detection (geometric / structural patterns)
# ─────────────────────────────────────────────────────────────────────────────

def _local_extrema(series: np.ndarray, order: int = 5) -> Tuple[List[int], List[int]]:
    """Find local maxima and minima indices using a comparison window."""
    highs, lows = [], []
    for i in range(order, len(series) - order):
        if all(series[i] >= series[i - j] for j in range(1, order + 1)) and \
           all(series[i] >= series[i + j] for j in range(1, order + 1)):
            highs.append(i)
        if all(series[i] <= series[i - j] for j in range(1, order + 1)) and \
           all(series[i] <= series[i + j] for j in range(1, order + 1)):
            lows.append(i)
    return highs, lows


def detect_chart_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detect geometric chart patterns over the full bar history."""
    hits: List[Dict[str, Any]] = []
    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    dates = df["date"].values
    n = len(df)

    if n < 30:
        return hits

    # Find pivots
    hi_idx, lo_idx = _local_extrema(h, order=5)
    _, lo_idx_c = _local_extrema(c, order=5)
    hi_idx_c, _ = _local_extrema(c, order=5)

    # ── Double Top ──────────────────────────────────────────────────────
    for a in range(len(hi_idx)):
        for b in range(a + 1, len(hi_idx)):
            ia, ib = hi_idx[a], hi_idx[b]
            if ib - ia < 10 or ib - ia > 80:
                continue
            # Tops within 2% of each other
            if abs(h[ia] - h[ib]) / h[ia] <= 0.02:
                # Trough between them
                trough = min(l[ia:ib+1])
                neckline = trough
                # Confirm breakdown (close below neckline after second top)
                if ib + 1 < n and c[ib] < neckline:
                    target = neckline - (h[ia] - neckline)
                    hits.append({
                        "pattern": "Double Top",
                        "signal": "bearish",
                        "date_range": f"{dates[ia]} → {dates[ib]}",
                        "level": f"Tops at ${h[ia]:.2f} / ${h[ib]:.2f}, neckline ${neckline:.2f}",
                        "target": f"${target:.2f}",
                        "desc": "Two equal highs with valley between — bearish reversal"
                    })
                    break
        else:
            continue
        break

    # ── Double Bottom ───────────────────────────────────────────────────
    for a in range(len(lo_idx)):
        for b in range(a + 1, len(lo_idx)):
            ia, ib = lo_idx[a], lo_idx[b]
            if ib - ia < 10 or ib - ia > 80:
                continue
            if abs(l[ia] - l[ib]) / l[ia] <= 0.02:
                peak = max(h[ia:ib+1])
                neckline = peak
                if ib + 1 < n and c[ib] > neckline:
                    target = neckline + (neckline - l[ia])
                    hits.append({
                        "pattern": "Double Bottom",
                        "signal": "bullish",
                        "date_range": f"{dates[ia]} → {dates[ib]}",
                        "level": f"Bottoms at ${l[ia]:.2f} / ${l[ib]:.2f}, neckline ${neckline:.2f}",
                        "target": f"${target:.2f}",
                        "desc": "Two equal lows with peak between — bullish reversal"
                    })
                    break
        else:
            continue
        break

    # ── Head & Shoulders ────────────────────────────────────────────────
    if len(hi_idx) >= 3:
        for i in range(len(hi_idx) - 2):
            li, head, ri = hi_idx[i], hi_idx[i+1], hi_idx[i+2]
            # Head must be highest
            if h[head] > h[li] and h[head] > h[ri]:
                # Shoulders roughly equal (within 5%)
                if abs(h[li] - h[ri]) / h[li] <= 0.05:
                    # Neckline = avg of troughs between shoulders
                    t1 = min(l[li:head+1])
                    t2 = min(l[head:ri+1])
                    neckline = (t1 + t2) / 2
                    height = h[head] - neckline
                    target = neckline - height
                    if ri + 1 < n and c[min(ri+3, n-1)] < neckline:
                        hits.append({
                            "pattern": "Head & Shoulders",
                            "signal": "bearish",
                            "date_range": f"{dates[li]} → {dates[ri]}",
                            "level": f"Head ${h[head]:.2f}, shoulders ${h[li]:.2f}/${h[ri]:.2f}, neckline ${neckline:.2f}",
                            "target": f"${target:.2f}",
                            "desc": "Classic reversal — head above two equal shoulders"
                        })
                        break

    # ── Inverse Head & Shoulders ────────────────────────────────────────
    if len(lo_idx) >= 3:
        for i in range(len(lo_idx) - 2):
            li, head, ri = lo_idx[i], lo_idx[i+1], lo_idx[i+2]
            if l[head] < l[li] and l[head] < l[ri]:
                if abs(l[li] - l[ri]) / l[li] <= 0.05:
                    t1 = max(h[li:head+1])
                    t2 = max(h[head:ri+1])
                    neckline = (t1 + t2) / 2
                    height = neckline - l[head]
                    target = neckline + height
                    if ri + 1 < n and c[min(ri+3, n-1)] > neckline:
                        hits.append({
                            "pattern": "Inverse Head & Shoulders",
                            "signal": "bullish",
                            "date_range": f"{dates[li]} → {dates[ri]}",
                            "level": f"Head ${l[head]:.2f}, shoulders ${l[li]:.2f}/${l[ri]:.2f}, neckline ${neckline:.2f}",
                            "target": f"${target:.2f}",
                            "desc": "Bullish reversal — inverted head below two equal shoulders"
                        })
                        break

    # ── Triangles (last 60 bars) ────────────────────────────────────────
    lookback = min(60, n - 1)
    recent_h = h[-lookback:]
    recent_l = l[-lookback:]
    recent_c = c[-lookback:]
    recent_dates = dates[-lookback:]

    hi_r, lo_r = _local_extrema(recent_h, order=3)
    _, lo_r_l = _local_extrema(recent_l, order=3)

    if len(hi_r) >= 2 and len(lo_r_l) >= 2:
        # Slopes of highs and lows
        h_slope = (recent_h[hi_r[-1]] - recent_h[hi_r[0]]) / max(hi_r[-1] - hi_r[0], 1)
        l_slope = (recent_l[lo_r_l[-1]] - recent_l[lo_r_l[0]]) / max(lo_r_l[-1] - lo_r_l[0], 1)

        range_pct = (recent_h[hi_r[0]] - recent_l[lo_r_l[0]]) / recent_l[lo_r_l[0]] * 100 if recent_l[lo_r_l[0]] > 0 else 0

        # Ascending triangle: flat highs, rising lows
        if abs(h_slope) < 0.02 and l_slope > 0.02 and range_pct > 3:
            hits.append({
                "pattern": "Ascending Triangle",
                "signal": "bullish",
                "date_range": f"{recent_dates[hi_r[0]]} → {recent_dates[hi_r[-1]]}",
                "level": f"Resistance ~${recent_h[hi_r[-1]]:.2f}, rising support",
                "desc": "Flat resistance + rising lows — bullish breakout expected"
            })

        # Descending triangle: falling highs, flat lows
        if h_slope < -0.02 and abs(l_slope) < 0.02 and range_pct > 3:
            hits.append({
                "pattern": "Descending Triangle",
                "signal": "bearish",
                "date_range": f"{recent_dates[lo_r_l[0]]} → {recent_dates[lo_r_l[-1]]}",
                "level": f"Support ~${recent_l[lo_r_l[-1]]:.2f}, falling resistance",
                "desc": "Flat support + falling highs — bearish breakdown expected"
            })

        # Symmetrical triangle: converging
        if h_slope < -0.02 and l_slope > 0.02 and range_pct > 3:
            hits.append({
                "pattern": "Symmetrical Triangle",
                "signal": "neutral",
                "date_range": f"{recent_dates[min(hi_r[0], lo_r_l[0])]} → present",
                "level": f"Converging between ${recent_l[lo_r_l[-1]]:.2f} - ${recent_h[hi_r[-1]]:.2f}",
                "desc": "Converging trendlines — breakout direction TBD"
            })

    # ── Flags (last 30 bars) ───────────────────────────────────────────
    flag_lb = min(30, n - 1)
    recent_30c = c[-flag_lb:]
    recent_30h = h[-flag_lb:]
    recent_30l = l[-flag_lb:]

    # Bull flag: strong up move then slight pullback channel
    if flag_lb >= 20:
        pole_start, pole_end = 0, flag_lb // 2
        flag_start, flag_end = flag_lb // 2, flag_lb - 1

        pole_gain = (recent_30c[pole_end] - recent_30c[pole_start]) / recent_30c[pole_start] * 100
        flag_change = (recent_30c[flag_end] - recent_30c[flag_start]) / recent_30c[flag_start] * 100

        if pole_gain > 5 and -5 < flag_change < 0:
            hits.append({
                "pattern": "Bull Flag",
                "signal": "bullish",
                "date_range": f"{dates[-flag_lb]} → {dates[-1]}",
                "level": f"Pole +{pole_gain:.1f}%, flag {flag_change:+.1f}%",
                "desc": "Strong rally followed by mild pullback — continuation bullish"
            })

        # Bear flag: strong down move then slight bounce
        if pole_gain < -5 and 0 < flag_change < 5:
            hits.append({
                "pattern": "Bear Flag",
                "signal": "bearish",
                "date_range": f"{dates[-flag_lb]} → {dates[-1]}",
                "level": f"Pole {pole_gain:+.1f}%, flag {flag_change:+.1f}%",
                "desc": "Strong selloff followed by mild bounce — continuation bearish"
            })

    # ── Wedges (last 50 bars) ──────────────────────────────────────────
    wedge_lb = min(50, n - 1)
    w_hi, w_lo = _local_extrema(h[-wedge_lb:], order=3)
    _, w_lo_l = _local_extrema(l[-wedge_lb:], order=3)

    if len(w_hi) >= 2 and len(w_lo_l) >= 2:
        wh_slope = (h[-wedge_lb:][w_hi[-1]] - h[-wedge_lb:][w_hi[0]]) / max(w_hi[-1] - w_hi[0], 1)
        wl_slope = (l[-wedge_lb:][w_lo_l[-1]] - l[-wedge_lb:][w_lo_l[0]]) / max(w_lo_l[-1] - w_lo_l[0], 1)

        # Rising wedge: both slopes positive but converging (high slope < low slope)
        if wh_slope > 0.01 and wl_slope > 0.01 and wl_slope > wh_slope:
            hits.append({
                "pattern": "Rising Wedge",
                "signal": "bearish",
                "date_range": f"{dates[-wedge_lb]} → present",
                "level": f"Converging upward channel",
                "desc": "Rising but narrowing — typically breaks down (bearish)"
            })

        # Falling wedge: both slopes negative but converging
        if wh_slope < -0.01 and wl_slope < -0.01 and abs(wl_slope) > abs(wh_slope):
            hits.append({
                "pattern": "Falling Wedge",
                "signal": "bullish",
                "date_range": f"{dates[-wedge_lb]} → present",
                "level": f"Converging downward channel",
                "desc": "Falling but narrowing — typically breaks up (bullish)"
            })

    # ── Channels (last 40 bars) ─────────────────────────────────────────
    ch_lb = min(40, n - 1)
    xs = np.arange(ch_lb)
    ch_h = h[-ch_lb:]
    ch_l = l[-ch_lb:]

    if ch_lb >= 20:
        h_fit = np.polyfit(xs, ch_h, 1)
        l_fit = np.polyfit(xs, ch_l, 1)

        # Parallel-ish slopes (within 30% of each other)
        if h_fit[0] != 0 and abs(l_fit[0] - h_fit[0]) / abs(h_fit[0]) < 0.30:
            if h_fit[0] > 0.02:
                hits.append({
                    "pattern": "Channel Up",
                    "signal": "bullish",
                    "date_range": f"{dates[-ch_lb]} → present",
                    "level": f"Slope: +${h_fit[0]:.3f}/bar",
                    "desc": "Price traveling in ascending parallel channel"
                })
            elif h_fit[0] < -0.02:
                hits.append({
                    "pattern": "Channel Down",
                    "signal": "bearish",
                    "date_range": f"{dates[-ch_lb]} → present",
                    "level": f"Slope: ${h_fit[0]:.3f}/bar",
                    "desc": "Price traveling in descending parallel channel"
                })

    # ── Support / Resistance levels ─────────────────────────────────────
    # Cluster analysis: find price levels where multiple pivots concentrate
    all_pivots = sorted(
        [h[j] for j in hi_idx[-10:]] + [l[j] for j in lo_idx[-10:]]
    ) if hi_idx and lo_idx else []

    if len(all_pivots) >= 4:
        clusters = []
        used = set()
        for p in all_pivots:
            if p in used:
                continue
            group = [q for q in all_pivots if abs(q - p) / p <= 0.015 and q not in used]
            if len(group) >= 2:
                level = sum(group) / len(group)
                clusters.append((level, len(group)))
                used.update(group)

        if clusters:
            clusters.sort(key=lambda x: -x[1])
            for lvl, cnt in clusters[:5]:
                kind = "RESISTANCE" if lvl > c[-1] else "SUPPORT"
                hits.append({
                    "pattern": f"Key {kind}",
                    "signal": "bullish" if kind == "SUPPORT" else "bearish",
                    "level": f"${lvl:.2f} ({cnt} touches)",
                    "desc": f"{kind.title()} zone with {cnt} pivot touches"
                })

    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Trend analysis helper
# ─────────────────────────────────────────────────────────────────────────────

def compute_trend_context(df: pd.DataFrame) -> Dict[str, Any]:
    c = df["close"]
    n = len(df)

    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()

    # ATR for volatility context
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - c.shift()).abs(),
        (df["low"] - c.shift()).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, adjust=False).mean()

    last_price = c.iloc[-1]
    ctx = {
        "last_close": round(float(last_price), 4),
        "sma20": round(float(sma20.iloc[-1]), 4) if not pd.isna(sma20.iloc[-1]) else None,
        "sma50": round(float(sma50.iloc[-1]), 4) if n >= 50 and not pd.isna(sma50.iloc[-1]) else None,
        "atr14": round(float(atr14.iloc[-1]), 4),
        "bars": n,
    }

    # Determine trend
    if ctx["sma20"] and ctx["sma50"]:
        if last_price > ctx["sma20"] > ctx["sma50"]:
            ctx["trend"] = "UPTREND"
        elif last_price < ctx["sma20"] < ctx["sma50"]:
            ctx["trend"] = "DOWNTREND"
        else:
            ctx["trend"] = "SIDEWAYS"
    elif ctx["sma20"]:
        ctx["trend"] = "UPTREND" if last_price > ctx["sma20"] else "DOWNTREND"
    else:
        ctx["trend"] = "N/A"

    # % changes
    for lb_name, lb in [("1w", 5), ("1m", 20), ("3m", 60), ("6m", 120), ("1y", 252)]:
        if n > lb:
            ctx[f"chg_{lb_name}"] = round((last_price - c.iloc[-lb-1]) / c.iloc[-lb-1] * 100, 2)

    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# Report printer
# ─────────────────────────────────────────────────────────────────────────────

def print_timeframe_report(
    label: str,
    df: pd.DataFrame,
    candle_hits: List[Dict[str, Any]],
    chart_hits: List[Dict[str, Any]],
    trend: Dict[str, Any],
):
    emoji_map = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}

    print("\n" + "█" * 74)
    print(f"█  {TICKER} — {label} TIMEFRAME  ({trend['bars']} bars)")
    print("█" * 74)

    # Trend context
    print(f"\n┌─ TREND CONTEXT ─────────────────────────────────────────────────")
    print(f"  Last Close : ${trend['last_close']:.2f}")
    print(f"  SMA(20)    : ${trend['sma20']}" if trend.get("sma20") else "  SMA(20)    : N/A (insufficient data)")
    print(f"  SMA(50)    : ${trend['sma50']}" if trend.get("sma50") else "  SMA(50)    : N/A")
    print(f"  ATR(14)    : ${trend['atr14']:.3f}")
    print(f"  Trend      : {trend['trend']}")

    changes = []
    for k, lbl in [("chg_1w", "1 week"), ("chg_1m", "1 month"), ("chg_3m", "3 months"),
                    ("chg_6m", "6 months"), ("chg_1y", "1 year")]:
        if k in trend:
            changes.append(f"  {lbl:<12}: {trend[k]:+.2f}%")
    if changes:
        print("  ── Performance ──")
        for ch in changes:
            print(ch)

    # Candlestick patterns
    print(f"\n┌─ CANDLESTICK PATTERNS (last {SCAN_WINDOW} bars) ──────────────────────")
    if candle_hits:
        bull = [p for p in candle_hits if p["signal"] == "bullish"]
        bear = [p for p in candle_hits if p["signal"] == "bearish"]
        neut = [p for p in candle_hits if p["signal"] == "neutral"]

        for group_label, group in [("BULLISH", bull), ("BEARISH", bear), ("NEUTRAL", neut)]:
            if group:
                print(f"\n  ── {group_label} patterns ({len(group)}) ──")
                for p in group:
                    e = emoji_map.get(p["signal"], "")
                    print(f"  {e} {p['date']}  {p['pattern']:<26} {p['desc']}")
    else:
        print("  No candlestick patterns detected in window")

    # Chart patterns
    print(f"\n┌─ CHART PATTERNS (structural / geometric) ──────────────────────")
    if chart_hits:
        # Separate actual patterns from support/resistance
        patterns = [p for p in chart_hits if not p["pattern"].startswith("Key ")]
        sr_levels = [p for p in chart_hits if p["pattern"].startswith("Key ")]

        if patterns:
            print(f"\n  ── Detected Formations ({len(patterns)}) ──")
            for p in patterns:
                e = emoji_map.get(p["signal"], "")
                print(f"  {e} {p['pattern']:<26} {p.get('date_range', '')}")
                if "level" in p:
                    print(f"     {p['level']}")
                if "target" in p:
                    print(f"     Target: {p['target']}")
                print(f"     {p['desc']}")

        if sr_levels:
            print(f"\n  ── Support / Resistance Levels ({len(sr_levels)}) ──")
            for p in sr_levels:
                e = emoji_map.get(p["signal"], "")
                print(f"  {e} {p['level']:<40} {p['desc']}")
    else:
        print("  No chart patterns detected")

    # Summary
    all_hits = candle_hits + chart_hits
    bull_count = sum(1 for p in all_hits if p["signal"] == "bullish")
    bear_count = sum(1 for p in all_hits if p["signal"] == "bearish")
    neut_count = sum(1 for p in all_hits if p["signal"] == "neutral")
    total = bull_count + bear_count + neut_count

    print(f"\n┌─ PATTERN SUMMARY ───────────────────────────────────────────────")
    print(f"  Total patterns found : {total}")
    print(f"  Bullish              : {bull_count}")
    print(f"  Bearish              : {bear_count}")
    print(f"  Neutral              : {neut_count}")

    if bull_count + bear_count > 0:
        score = bull_count / (bull_count + bear_count) * 100
        bias = "🟢 BULLISH bias" if score >= 60 else ("🔴 BEARISH bias" if score <= 40 else "⚪ MIXED / NEUTRAL")
        print(f"  Pattern bias         : {bias} ({score:.0f}% bullish)")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print(f"\n▶ Fetching {TICKER} OHLCV bars — DAILY + WEEKLY from Polygon...")

    with ThreadPoolExecutor(max_workers=2) as pool:
        daily_future  = pool.submit(fetch_bars, "day")
        weekly_future = pool.submit(fetch_bars, "week")

    daily_df  = daily_future.result()
    weekly_df = weekly_future.result()

    print(f"  ✓ Data loaded in {time.time()-t0:.1f}s")

    for label, df in [("DAILY", daily_df), ("WEEKLY", weekly_df)]:
        if df is None or df.empty:
            print(f"\n✗ No {label} data — skipping")
            continue

        print(f"\n▶ Analyzing {label} ({len(df)} bars)...")
        trend = compute_trend_context(df)
        candle_hits = detect_candlestick_patterns(df, window=SCAN_WINDOW)
        chart_hits  = detect_chart_patterns(df)
        print_timeframe_report(label, df, candle_hits, chart_hits, trend)

    # Cross-timeframe verdict
    print("█" * 74)
    print("█  CROSS-TIMEFRAME VERDICT")
    print("█" * 74)

    all_patterns = []
    for label, df in [("DAILY", daily_df), ("WEEKLY", weekly_df)]:
        if df is not None and not df.empty:
            candle = detect_candlestick_patterns(df, window=SCAN_WINDOW)
            chart  = detect_chart_patterns(df)
            for p in candle + chart:
                p["timeframe"] = label
            all_patterns.extend(candle + chart)

    bull_total = sum(1 for p in all_patterns if p["signal"] == "bullish")
    bear_total = sum(1 for p in all_patterns if p["signal"] == "bearish")
    total = bull_total + bear_total

    if total > 0:
        score = bull_total / total * 100
        if score >= 65:
            verdict = "🟢 BULLISH — majority patterns point up across both timeframes"
        elif score <= 35:
            verdict = "🔴 BEARISH — majority patterns point down across both timeframes"
        elif score >= 55:
            verdict = "🟢 LEAN BULLISH — slight bullish edge in pattern analysis"
        elif score <= 45:
            verdict = "🔴 LEAN BEARISH — slight bearish edge in pattern analysis"
        else:
            verdict = "⚪ NEUTRAL — conflicting signals across timeframes"
    else:
        score = 50
        verdict = "⚪ INCONCLUSIVE — insufficient patterns detected"

    print(f"\n  Combined patterns    : {len(all_patterns)}")
    print(f"  Bullish              : {bull_total}")
    print(f"  Bearish              : {bear_total}")
    print(f"  Confluence score     : {score:.0f}%")
    print(f"  Verdict              : {verdict}")
    print(f"\n  Total time: {time.time()-t0:.2f}s")
    print()


if __name__ == "__main__":
    main()
