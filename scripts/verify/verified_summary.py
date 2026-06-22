"""Build dashboard-friendly verified TP summary from verification row results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import RowVerification, VerifyRow


def _is_bullish(signal: Optional[str]) -> bool:
    s = (signal or "").strip().lower()
    return s in ("bullish", "buy")


def _artifact_technical_bucket(row: VerifyRow) -> Optional[str]:
    """Mirror technical backtest confusion: bullish + signal_correct → TP/FP."""
    sig = row.fusion_final_signal or row.technical_signal
    if not _is_bullish(sig):
        return None
    if row.signal_correct is True:
        return "TP"
    if row.signal_correct is False:
        return "FP"
    return "UNLABELED"


def _check_value(rv: RowVerification, field: str) -> Optional[Any]:
    for chk in rv.checks:
        if chk.field == field:
            return chk.actual
    return None


def _target_hit_verified(rv: RowVerification) -> Optional[bool]:
    for chk in rv.checks:
        if chk.field == "target_hit":
            if chk.status == "SKIP":
                return None
            return chk.actual if chk.status == "PASS" else chk.actual
    return None


def _row_fully_confirmed(rv: RowVerification) -> bool:
    if rv.status != "PASS":
        return False
    critical = {"entry_price", "target_hit"}
    for chk in rv.checks:
        if chk.field in critical and chk.status == "FAIL":
            return False
    return True


def build_verified_summary(
    row_results: List[RowVerification],
    *,
    agent: str = "technical",
) -> Dict[str, Any]:
    """
    Summarize Polygon-verified bullish true positives vs artifact claims.

    *agent* ``technical`` uses ``fusion_final_signal`` / ``signal_correct`` (technical backtest lab).
    """
    artifact_tp: List[Dict[str, Any]] = []
    artifact_fp: List[Dict[str, Any]] = []
    verified_tp: List[Dict[str, Any]] = []
    disputed_tp: List[Dict[str, Any]] = []
    verified_fp: List[Dict[str, Any]] = []
    disputed_fp: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for rv in row_results:
        row = rv.row
        bucket = _artifact_technical_bucket(row)
        if bucket is None:
            continue

        entry = {
            "ticker": row.ticker,
            "signal_date": row.signal_date,
            "result_date": row.result_date,
            "fusion_final_signal": row.fusion_final_signal,
            "technical_signal": row.technical_signal,
            "artifact_target_hit": row.target_hit,
            "artifact_signal_correct": row.signal_correct,
            "entry_price": row.entry_price,
            "target_price": row.target_price,
            "target_hit_date": row.target_hit_date,
            "verification_status": rv.status,
            "recomputed_target_hit": _check_value(rv, "target_hit"),
            "recomputed_entry_price": _check_value(rv, "entry_price"),
        }

        if rv.status == "SKIP":
            skipped.append({**entry, "detail": next((c.detail for c in rv.checks if c.detail), None)})
            continue

        confirmed = _row_fully_confirmed(rv)
        recomputed_hit = _target_hit_verified(rv)

        if bucket == "TP":
            artifact_tp.append(entry)
            if confirmed and recomputed_hit is True:
                verified_tp.append({**entry, "polygon_confirmed": True})
            else:
                disputed_tp.append(
                    {
                        **entry,
                        "polygon_confirmed": False,
                        "mismatches": [
                            {"field": c.field, "expected": c.expected, "actual": c.actual}
                            for c in rv.checks
                            if c.status == "FAIL"
                        ],
                    }
                )
        elif bucket == "FP":
            artifact_fp.append(entry)
            if confirmed and recomputed_hit is False:
                verified_fp.append({**entry, "polygon_confirmed": True})
            else:
                disputed_fp.append(
                    {
                        **entry,
                        "polygon_confirmed": False,
                        "mismatches": [
                            {"field": c.field, "expected": c.expected, "actual": c.actual}
                            for c in rv.checks
                            if c.status == "FAIL"
                        ],
                    }
                )

    n_tp = len(artifact_tp)
    n_fp = len(artifact_fp)
    return {
        "agent": agent,
        "description": (
            "Bullish signals (fusion_final_signal) cross-checked against independent Polygon "
            "price/outcome recomputation. Confirmed TP = artifact TP and all Polygon checks pass."
        ),
        "artifact_claimed": {
            "bullish_tp": n_tp,
            "bullish_fp": n_fp,
            "bullish_total": n_tp + n_fp,
        },
        "polygon_verified": {
            "confirmed_tp": len(verified_tp),
            "disputed_tp": len(disputed_tp),
            "confirmed_fp": len(verified_fp),
            "disputed_fp": len(disputed_fp),
            "skipped_bullish": len(skipped),
            "tp_confirmation_rate_pct": round(len(verified_tp) / n_tp * 100, 1) if n_tp else None,
            "price_rows_pass": sum(1 for r in row_results if r.status == "PASS"),
            "price_rows_fail": sum(1 for r in row_results if r.status == "FAIL"),
            "price_rows_skip": sum(1 for r in row_results if r.status == "SKIP"),
        },
        "verified_tp_tickers": sorted(verified_tp, key=lambda x: x["ticker"]),
        "disputed_tp_tickers": sorted(disputed_tp, key=lambda x: x["ticker"]),
        "verified_fp_tickers": sorted(verified_fp, key=lambda x: x["ticker"]),
        "disputed_fp_tickers": sorted(disputed_fp, key=lambda x: x["ticker"]),
        "skipped_bullish_tickers": sorted(skipped, key=lambda x: x["ticker"]),
    }
