"""
backtest_phoenix.py — Monthly backtest engine for an orchestrator variant:
Phoenix + Fundamental → CWAF fusion.

Price + target-hit evaluation use **Polygon** only (no Yahoo) when
``POLYGON_API_KEY`` is configured.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from agents.polygon_data import PolygonClient

from .config import OrchestratorSettings
from .fusion_phoenix import _extract_phoenix_output, fuse_signals_phoenix


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _polygon_client() -> PolygonClient:
    return PolygonClient()


def _polygon_download_daily_between(ticker: str, start: date, end: date) -> Any:
    """One Polygon pull for [start, end] — used for target-hit highs."""
    client = _polygon_client()
    if not client.is_available():
        return None
    try:
        return client.fetch_daily_between(ticker, start, end)
    except Exception:
        return None


def _compute_target(
    phoenix_result: Optional[Dict[str, Any]],
    entry_price: float,
) -> Optional[float]:
    """
    Determine a target price for the evaluation window.

    Preference:
      1) Phoenix risk.target_1 (if available)
      2) Fallback: +5% target
    """
    if phoenix_result:
        risk = phoenix_result.get("risk") or {}
        t1 = _safe_float(risk.get("target_1"))
        if t1 and t1 > 0:
            return t1
    return round(entry_price * 1.05, 2)


def _target_hit_within_window(
    ticker: str,
    start: date,
    end: date,
    target_price: float,
    daily_bars: Any = None,
) -> Dict[str, Any]:
    """
    Check whether price reached target_price at any point in [start, end].
    Uses Polygon daily bars (High).
    """
    try:
        import pandas as pd
    except Exception as exc:
        return {"target_hit": None, "target_hit_date": None, "error": f"pandas import failed: {exc}"}

    try:
        df = daily_bars
        if df is None:
            df = _polygon_download_daily_between(ticker, start, end)
        if df is None or df.empty:
            return {"target_hit": None, "target_hit_date": None, "error": "No bars in window"}
        if isinstance(df.columns, pd.MultiIndex):
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


def _download_daily_bars(ticker: str, start: date, end: date) -> Any:
    """One Polygon daily-bar dataframe covering [start, end] (whole backtest horizon)."""
    return _polygon_download_daily_between(ticker, start, end)


def _close_on_or_before(
    daily_bars: Any,
    d: date,
) -> Tuple[Optional[float], Optional[str]]:
    """Last adjusted close on or before *d* from a Polygon OHLCV dataframe."""
    try:
        import pandas as pd
    except Exception:
        return None, None
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


def _polygon_start_price(ticker: str, signal_date: date) -> Tuple[Optional[float], Optional[str]]:
    client = _polygon_client()
    if not client.is_available():
        return None, None
    got = client.get_close_price(ticker, signal_date)
    if not got:
        return None, None
    price, bar_d = got
    return float(price), bar_d.isoformat()


def _correctness_for_signal(
    signal_name: str,
    target_eval: Dict[str, Any],
) -> Optional[bool]:
    hit = target_eval.get("target_hit")
    if signal_name == "bullish":
        return True if hit is True else (False if hit is False else None)
    if signal_name == "bearish":
        return True if hit is False else (False if hit is True else None)
    return None


def run_monthly_backtest(
    ticker: str,
    months: List[Tuple[date, date]],
    settings: Optional[OrchestratorSettings] = None,
    period_workers: int = 1,
) -> Dict[str, Any]:
    """
    Run Phoenix+Fund orchestrator backtest over (signal_date, result_date) pairs.

    ``period_workers > 1`` evaluates calendar months concurrently (still one Polygon
    pull per ticker for the full horizon).
    """
    cfg = settings or OrchestratorSettings()

    month_pairs = list(months)
    pw = max(1, min(int(period_workers or 1), len(month_pairs) or 1))

    if month_pairs:
        min_start = min(d for d, _ in month_pairs)
        max_end = max(d for _, d in month_pairs)
        daily_bars = _download_daily_bars(ticker, min_start, max_end)
    else:
        daily_bars = None

    if pw <= 1 or len(month_pairs) <= 1:
        periods = [
            _run_period(
                ticker=ticker,
                signal_date=sd,
                result_date=rd,
                settings=cfg,
                daily_bars=daily_bars,
            )
            for sd, rd in month_pairs
        ]
    else:
        with ThreadPoolExecutor(max_workers=pw) as pool:
            futs = {
                pool.submit(
                    _run_period,
                    ticker,
                    sd,
                    rd,
                    cfg,
                    daily_bars,
                ): idx
                for idx, (sd, rd) in enumerate(month_pairs)
            }
            periods = [None] * len(month_pairs)
            for fut in as_completed(futs):
                idx = futs[fut]
                periods[idx] = fut.result()

    directional_f = [p for p in periods if p.get("signal_correct") is not None]
    correct_f = sum(1 for p in directional_f if p["signal_correct"])
    acc_f = (correct_f / len(directional_f) * 100.0) if directional_f else None

    directional_p = [p for p in periods if p.get("signal_correct_phoenix") is not None]
    correct_p = sum(1 for p in directional_p if p["signal_correct_phoenix"])
    acc_p = (correct_p / len(directional_p) * 100.0) if directional_p else None

    n = len(periods)
    warn = (
        f"This covers {n} month{'s' if n != 1 else ''} on one stock. "
        f"{n} data point{'s are' if n != 1 else ' is'} not statistically "
        "significant — use this to understand the signal behaviour, not "
        "to validate it."
    )

    return {
        "ticker": ticker.upper(),
        "periods": periods,
        "summary": {
            "total_periods": n,
            "directional_signals": len(directional_f),
            "correct_signals": correct_f,
            "accuracy_pct": round(acc_f, 1) if acc_f is not None else None,
            "warning": warn,
            "basis": "orchestrator_fusion_signal_vs_target_hit",
        },
        "summary_phoenix": {
            "total_periods": n,
            "directional_signals": len(directional_p),
            "correct_signals": correct_p,
            "accuracy_pct": round(acc_p, 1) if acc_p is not None else None,
            "warning": warn,
            "basis": "phoenix_signal_vs_target_hit",
        },
    }


def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    settings: OrchestratorSettings,
    daily_bars: Any = None,
) -> Dict[str, Any]:
    """
    Signal generation uses ``as_of_date=signal_date`` for Phoenix + FA only.
    No future OHLCV or fundamentals are passed into those agents. Forward
    prices (target window, exit reference) are used only *after* ``signal_date``
    for outcome labeling — never as inputs to the screening models.
    """
    from agents.phoenix.service import analyze_ticker as phoenix_analyze
    from agents.fundamental.service import analyze_ticker as fund_analyze

    phoenix_result: Optional[Dict[str, Any]] = None
    phoenix_error: Optional[str] = None
    fund_result: Optional[Dict[str, Any]] = None
    fund_error: Optional[str] = None

    try:
        phoenix_result = phoenix_analyze(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
        )
    except Exception as exc:
        phoenix_error = str(exc)

    try:
        fund_result = fund_analyze(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
            data_source=settings.fund_data_source,
        )
    except Exception as exc:
        fund_error = str(exc)

    fusion = fuse_signals_phoenix(
        phoenix_result=phoenix_result,
        phoenix_error=phoenix_error,
        fund_result=fund_result,
        fund_error=fund_error,
        settings=settings,
    )

    signal = fusion.final_signal

    if phoenix_result and not phoenix_error:
        px_out = _extract_phoenix_output(phoenix_result, list(settings.tech_thresholds))
        phoenix_signal = px_out.signal
    else:
        phoenix_signal = "neutral"

    start_price, start_price_date = _polygon_start_price(ticker, signal_date)
    exit_px, exit_px_date = _close_on_or_before(daily_bars, result_date)

    tl_merge: Dict[str, Any] = {}
    if phoenix_result and isinstance(phoenix_result.get("trade_levels"), dict):
        tl_merge = dict(phoenix_result["trade_levels"])
    if exit_px is not None:
        tl_merge["exit_reference_price"] = exit_px
        tl_merge["exit_reference_date"] = exit_px_date

    if start_price is None:
        return {
            "month": signal_date.strftime("%B %Y"),
            "signal_date": signal_date.isoformat(),
            "result_date": result_date.isoformat(),
            "error": "Polygon start price unavailable — check POLYGON_API_KEY / listing / date.",
            "signal": signal,
            "signal_correct": None,
            "phoenix_signal": phoenix_signal,
            "signal_correct_phoenix": None,
            "start_price_source": "polygon",
            "trade_levels": tl_merge or None,
            "exit_reference_price": exit_px,
            "exit_reference_date": exit_px_date,
            "phoenix_error": phoenix_error,
            "fund_error": fund_error,
        }

    target_price = _compute_target(phoenix_result, float(start_price))
    target_eval = (
        _target_hit_within_window(ticker, signal_date, result_date, float(target_price), daily_bars=daily_bars)
        if target_price
        else {"target_hit": None, "target_hit_date": None, "error": "No target price"}
    )

    correct_fusion = _correctness_for_signal(signal, target_eval)
    correct_px = _correctness_for_signal(phoenix_signal, target_eval)

    phoenix_score = fusion.tech_output.score if fusion.tech_output else None
    fund_score = fusion.fund_output.score if fusion.fund_output else None

    return {
        "month": signal_date.strftime("%B %Y"),
        "signal_date": signal_date.isoformat(),
        "result_date": result_date.isoformat(),
        "start_price": round(float(start_price), 2),
        "start_price_date": str(start_price_date),
        "start_price_source": "polygon",
        "exit_reference_price": exit_px,
        "exit_reference_date": exit_px_date,
        "trade_levels": tl_merge or None,
        "target_price": round(float(target_price), 2) if target_price else None,
        "target_hit": target_eval.get("target_hit"),
        "target_hit_date": target_eval.get("target_hit_date"),
        "target_eval_error": target_eval.get("error"),
        "target_data_source": "polygon",
        "orchestrator_score": fusion.orchestrator_score,
        "signal": signal,
        "signal_correct": correct_fusion,
        "phoenix_signal": phoenix_signal,
        "signal_correct_phoenix": correct_px,
        "confidence": fusion.final_confidence,
        "conflict_detected": fusion.conflict_detected,
        "conflict_resolution": fusion.conflict_resolution,
        "weights_applied": fusion.weights_applied,
        "phoenix_score": phoenix_score,
        "fund_score": fund_score,
        "phoenix_error": phoenix_error,
        "fund_error": fund_error,
        "extension_guardrail": (
            phoenix_result.get("extension_guardrail") if phoenix_result else None
        ),
    }
