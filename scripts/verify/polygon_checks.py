"""
Independent Polygon price/outcome recomputation for audit verification.

Logic mirrors agents/orchestrator/backtest_phoenix.py but is duplicated here
on purpose — this module must not import backtest engine code.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .models import VerifyRow


def close_on_or_before(daily_bars: Any, d: date) -> Tuple[Optional[float], Optional[str]]:
    """Last adjusted close on or before *d* from a Polygon OHLCV dataframe."""
    if daily_bars is None:
        return None, None
    try:
        df = daily_bars
        if getattr(df, "empty", True):
            return None, None
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return None, None
        try:
            mask = df.index.map(lambda x: x.date() <= d)
        except Exception:
            return None, None
        sub = df.loc[mask]
        if sub.empty:
            return None, None
        last = sub.iloc[-1]
        dt = sub.index[-1]
        bar_d = dt.date().isoformat() if hasattr(dt, "date") else str(dt)
        return round(float(last["Close"]), 2), bar_d
    except Exception:
        return None, None


def target_hit_within_window(
    start: date,
    end: date,
    target_price: float,
    daily_bars: Any,
) -> Dict[str, Any]:
    """True if any daily High >= target_price in [start, end] inclusive."""
    try:
        df = daily_bars
        if df is None or getattr(df, "empty", True):
            return {"target_hit": None, "target_hit_date": None, "error": "No bars in window"}
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
        if "High" not in df.columns:
            return {"target_hit": None, "target_hit_date": None, "error": "High column missing"}
        try:
            dfw = df[(df.index.date >= start) & (df.index.date <= end)]
        except Exception:
            dfw = df
        hit = dfw["High"] >= float(target_price)
        if not bool(hit.any()):
            return {"target_hit": False, "target_hit_date": None, "error": None}
        first_idx = hit[hit].index[0]
        hit_date = first_idx.date().isoformat() if hasattr(first_idx, "date") else str(first_idx)
        return {"target_hit": True, "target_hit_date": hit_date, "error": None}
    except Exception as exc:
        return {"target_hit": None, "target_hit_date": None, "error": str(exc)}


def correctness_for_signal(signal_name: Optional[str], target_eval: Dict[str, Any]) -> Optional[bool]:
    hit = target_eval.get("target_hit")
    sig = (signal_name or "").lower()
    if sig == "bullish":
        return True if hit is True else (False if hit is False else None)
    if sig == "bearish":
        return True if hit is False else (False if hit is True else None)
    return None


def _parse_date(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


class PolygonVerifier:
    """Fetch Polygon bars and recompute price/outcome fields for one row."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._bar_cache: Dict[Tuple[str, str, str], Any] = {}

    def _fetch_bars(self, ticker: str, start: date, end: date) -> Any:
        key = (ticker.upper(), start.isoformat(), end.isoformat())
        if key not in self._bar_cache:
            self._bar_cache[key] = self._client.fetch_daily_between(ticker, start, end)
        return self._bar_cache[key]

    def recompute_row(self, row: VerifyRow) -> Dict[str, Any]:
        """Return independently recomputed Polygon-derived fields for *row*."""
        out: Dict[str, Any] = {
            "entry_price": None,
            "start_price_date": None,
            "exit_reference_price": None,
            "exit_reference_date": None,
            "target_hit": None,
            "target_hit_date": None,
            "signal_correct": None,
            "signal_correct_technical": None,
            "signal_correct_phoenix": None,
            "polygon_error": None,
        }
        if row.error and row.entry_price is None and row.target_hit is None:
            out["polygon_error"] = "Skipped row with artifact error and no price fields"
            return out
        if not row.signal_date or not row.result_date:
            out["polygon_error"] = "Missing signal_date or result_date"
            return out

        try:
            sig = _parse_date(row.signal_date)
            res = _parse_date(row.result_date)
        except ValueError as exc:
            out["polygon_error"] = str(exc)
            return out

        if not self._client.is_available():
            out["polygon_error"] = "POLYGON_API_KEY not configured"
            return out

        bars = self._fetch_bars(row.ticker, sig, res)
        if bars is None or getattr(bars, "empty", True):
            got = self._client.get_close_price(row.ticker, sig)
            if not got:
                out["polygon_error"] = f"No Polygon bars for {row.ticker} [{sig}, {res}]"
                return out
            price, bar_d = got
            out["entry_price"] = round(float(price), 2)
            out["start_price_date"] = bar_d.isoformat()
            out["polygon_error"] = "Partial bars only — target_hit not recomputed"
            return out

        entry_px, entry_dt = close_on_or_before(bars, sig)
        exit_px, exit_dt = close_on_or_before(bars, res)
        out["entry_price"] = entry_px
        out["start_price_date"] = entry_dt
        out["exit_reference_price"] = exit_px
        out["exit_reference_date"] = exit_dt

        if row.target_price is not None and row.target_price > 0:
            te = target_hit_within_window(sig, res, float(row.target_price), bars)
            out["target_hit"] = te.get("target_hit")
            out["target_hit_date"] = te.get("target_hit_date")
            if te.get("error"):
                out["polygon_error"] = te.get("error")

            fusion_sig = row.fusion_final_signal or row.technical_signal
            out["signal_correct"] = correctness_for_signal(fusion_sig, te)
            out["signal_correct_technical"] = correctness_for_signal(row.technical_signal, te)
            phoenix_dir = row.phoenix_signal
            if phoenix_dir and phoenix_dir.upper() in ("BUY", "WATCH", "AVOID"):
                from_map = {"BUY": "bullish", "WATCH": "neutral", "AVOID": "bearish"}
                phoenix_dir = from_map.get(phoenix_dir.upper(), phoenix_dir)
            out["signal_correct_phoenix"] = correctness_for_signal(phoenix_dir, te)

        return out
