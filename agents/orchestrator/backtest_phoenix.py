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
    *,
    strategy_profile: str = "blend",
    evaluate_intelligence: bool = False,
    technical_only: bool = True,
    backtest_signal_profile: str = "phoenix_recall",
) -> Dict[str, Any]:
    """
    Run Phoenix+Fund orchestrator backtest over (signal_date, result_date) pairs.

    ``backtest_signal_profile`` controls how ``technical_signal`` is mapped for
    confusion-matrix evaluation when ``technical_only=True`` (see
    ``agents.technical.backtest_signal``).

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
                strategy_profile=strategy_profile,
                evaluate_intelligence=evaluate_intelligence and not technical_only,
                technical_only=technical_only,
                backtest_signal_profile=backtest_signal_profile,
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
                    strategy_profile=strategy_profile,
                    evaluate_intelligence=evaluate_intelligence and not technical_only,
                    technical_only=technical_only,
                    backtest_signal_profile=backtest_signal_profile,
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

    directional_t = [p for p in periods if p.get("signal_correct_technical") is not None]
    correct_t = sum(1 for p in directional_t if p["signal_correct_technical"])
    acc_t = (correct_t / len(directional_t) * 100.0) if directional_t else None

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
            "basis": (
                "technical_signal_vs_target_hit"
                if technical_only
                else "orchestrator_fusion_signal_vs_target_hit"
            ),
        },
        "summary_phoenix": {
            "total_periods": n,
            "directional_signals": len(directional_p),
            "correct_signals": correct_p,
            "accuracy_pct": round(acc_p, 1) if acc_p is not None else None,
            "warning": warn,
            "basis": "phoenix_signal_vs_target_hit",
        },
        "summary_technical": {
            "total_periods": n,
            "directional_signals": len(directional_t),
            "correct_signals": correct_t,
            "accuracy_pct": round(acc_t, 1) if acc_t is not None else None,
            "warning": warn,
            "basis": "technical_fusion_signal_vs_target_hit",
        },
    }


def _run_period(
    ticker: str,
    signal_date: date,
    result_date: date,
    settings: OrchestratorSettings,
    daily_bars: Any = None,
    *,
    strategy_profile: str = "blend",
    evaluate_intelligence: bool = False,
    technical_only: bool = True,
    backtest_signal_profile: str = "phoenix_recall",
) -> Dict[str, Any]:
    """
    Signal generation uses ``as_of_date=signal_date`` for Technical (Phoenix + strategies)
    only when ``technical_only=True`` (default). FA and intelligence are skipped.

    Forward prices (target window, exit reference) are used only *after* ``signal_date``
    for outcome labeling — never as inputs to the screening models.
    """
    from agents.technical.service import analyze_technical

    if not technical_only:
        from agents.fundamental.service import analyze_ticker as fund_analyze
        from agents.orchestrator.fusion import _extract_fund_output
        from .fusion_phoenix import fuse_signals_phoenix

    technical_result: Optional[Dict[str, Any]] = None
    technical_error: Optional[str] = None
    phoenix_result: Optional[Dict[str, Any]] = None
    phoenix_error: Optional[str] = None
    fund_result: Optional[Dict[str, Any]] = None
    fund_error: Optional[str] = None

    try:
        technical_result = analyze_technical(
            ticker=ticker,
            as_of_date=signal_date.isoformat(),
            strategy_profile=strategy_profile,
        )
        if not technical_result.get("ok"):
            technical_error = technical_result.get("error") or "Technical agent failed"
        phoenix_result = technical_result.get("phoenix") or {}
    except Exception as exc:
        technical_error = str(exc)
        phoenix_error = str(exc)

    fund_result = None
    fund_error = None
    if not technical_only:
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
            phoenix_error=phoenix_error or technical_error,
            fund_result=fund_result,
            fund_error=fund_error,
            settings=settings,
        )
        signal = fusion.final_signal
        technical_signal_live = (technical_result or {}).get("signal") or "neutral"
        technical_signal = technical_signal_live
        technical_fusion = (technical_result or {}).get("technical_fusion") or {}
    else:
        from agents.technical.backtest_signal import derive_backtest_signal
        from agents.technical.fusion import build_technical_fusion

        layers_pre = (technical_result or {}).get("strategy_layers") or {}
        technical_fusion = (technical_result or {}).get("technical_fusion") or {}
        _fusion_obj = build_technical_fusion(phoenix_result or {}, layers_pre)
        technical_signal_live = (technical_result or {}).get("signal") or "neutral"
        technical_signal = derive_backtest_signal(
            phoenix_result or {},
            _fusion_obj,
            profile=backtest_signal_profile,
        )
        signal = technical_signal

    if phoenix_result and not phoenix_error:
        px_out = _extract_phoenix_output(phoenix_result, list(settings.tech_thresholds))
        phoenix_signal = px_out.signal
    else:
        phoenix_signal = "neutral"

    # Long-only matrix mapping (technical-only backtests only):
    # Phoenix has no explicit short thesis — AVOID/WATCH mean "no buy setup", not
    # "predict a drop". Forcing AVOID into `bearish` produces massive false
    # negatives whenever the broad tape rebounds. Two cases count as bullish:
    #   - BUY  (standard trend continuation)
    #   - WATCH with phoenix_entry_mode == "recovery_upgrade" (Phase 2 reversal)
    # Live fusion path (technical_only=False) keeps the original mapping.
    if technical_only:
        raw_phoenix = str((phoenix_result or {}).get("signal") or "").upper()
        entry_mode = str((phoenix_result or {}).get("phoenix_entry_mode") or "standard")
        if raw_phoenix == "BUY" or (raw_phoenix == "WATCH" and entry_mode == "recovery_upgrade"):
            phoenix_signal = "bullish"
        else:
            phoenix_signal = "neutral"

    fund_signal = "neutral"
    if not technical_only and fund_result and not fund_error:
        fund_out = _extract_fund_output(fund_result, list(settings.fund_thresholds))
        fund_signal = fund_out.signal

    layers = (technical_result or {}).get("strategy_layers") or {}
    strategy_signals = {
        sid: str((layer or {}).get("signal") or "neutral")
        for sid, layer in layers.items()
    }

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
            "technical_signal": technical_signal,
            "signal_correct_technical": None,
            "fund_signal": fund_signal,
            "signal_correct_fundamental": None,
            "technical_fusion": technical_fusion,
            "start_price_source": "polygon",
            "trade_levels": tl_merge or None,
            "exit_reference_price": exit_px,
            "exit_reference_date": exit_px_date,
            "phoenix_error": phoenix_error,
            "technical_error": technical_error,
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
    correct_technical = _correctness_for_signal(technical_signal, target_eval)
    correct_fund = (
        _correctness_for_signal(fund_signal, target_eval) if not technical_only else None
    )
    strategy_correct = {
        sid: _correctness_for_signal(sig, target_eval) for sid, sig in strategy_signals.items()
    }

    phoenix_score = None
    fund_score = None
    if not technical_only:
        phoenix_score = fusion.tech_output.score if fusion.tech_output else None
        fund_score = fusion.fund_output.score if fusion.fund_output else None
    else:
        phoenix_score = phoenix_result.get("score") if phoenix_result else None

    period: Dict[str, Any] = {
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
        "orchestrator_score": (
            fusion.orchestrator_score if not technical_only else (technical_result or {}).get("score")
        ),
        "signal": signal,
        "signal_correct": correct_technical if technical_only else correct_fusion,
        "phoenix_signal": phoenix_signal,
        "signal_correct_phoenix": correct_px,
        "technical_signal": technical_signal,
        "signal_correct_technical": correct_technical,
        "fund_signal": fund_signal,
        "signal_correct_fundamental": correct_fund,
        "technical_fusion": technical_fusion,
        "technical_score": (technical_result or {}).get("score"),
        "strategy_layers": layers,
        "confidence": (
            fusion.final_confidence if not technical_only else (technical_result or {}).get("confidence")
        ),
        "conflict_detected": fusion.conflict_detected if not technical_only else False,
        "conflict_resolution": fusion.conflict_resolution if not technical_only else None,
        "weights_applied": fusion.weights_applied if not technical_only else None,
        "phoenix_score": phoenix_score,
        "fund_score": fund_score,
        "phoenix_error": phoenix_error,
        "technical_error": technical_error,
        "fund_error": fund_error if not technical_only else None,
        "technical_only": technical_only,
        "backtest_signal_profile": backtest_signal_profile,
        "technical_signal_live": technical_signal_live,
        "hard_filter_passed": bool((phoenix_result or {}).get("hard_filter_passed")),
        "extension_guardrail": (
            phoenix_result.get("extension_guardrail") if phoenix_result else None
        ),
        "phoenix_raw_signal": (
            str((phoenix_result or {}).get("signal") or "").upper() or None
        ),
        "phoenix_entry_mode": (phoenix_result or {}).get("phoenix_entry_mode"),
    }
    for sid, sig in strategy_signals.items():
        period[f"{sid}_signal"] = sig
        period[f"signal_correct_{sid}"] = strategy_correct.get(sid)

    if evaluate_intelligence and not technical_only:
        from .backtest_intelligence import apply_intelligence_correctness, evaluate_intelligence_layer

        intel = evaluate_intelligence_layer(
            ticker=ticker,
            signal_date=signal_date,
            phoenix_result=phoenix_result,
            fund_result=fund_result,
            technical_result=technical_result,
            settings=settings,
        )
        period.update(intel)
        apply_intelligence_correctness(period, target_eval)

    return period
