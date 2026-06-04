"""
run_bundle.py — Stable JSON aggregates for UI + run-vs-run comparison.

Schema version is bumped only when fields are added with backward-compatible defaults,
or when breaking changes are documented in CHANGELOG / BACKTEST_PLAYBOOK.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_ticker_sector_map() -> Dict[str, str]:
    """Upper ticker -> sector name from halal_sector_tickers.json."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from data.halal_universe import load_sector_tickers  # noqa: E402

    out: Dict[str, str] = {}
    for sector, tickers in load_sector_tickers().items():
        for t in tickers:
            out[str(t).upper()] = sector
    return out


def _fund_signal_from_eval(fund: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    from agents.orchestrator.models import BAND_TO_SIGNAL  # noqa: E402

    es = fund.get("experimental_score") or {}
    if not es.get("available"):
        return None, None
    band = es.get("band")
    sig = BAND_TO_SIGNAL.get(str(band), "neutral") if band else "neutral"
    score = es.get("score")
    try:
        sc = float(score) if score is not None else None
    except (TypeError, ValueError):
        sc = None
    return sig, sc


def _phoenix_direction(px_signal: Optional[str]) -> str:
    s = (px_signal or "WATCH").upper()
    if s == "BUY":
        return "bullish"
    if s == "AVOID":
        return "bearish"
    return "neutral"


def trade_levels_from_phoenix(px: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten Phoenix trade snapshot for run_bundle rows (stable keys for UI)."""
    tl = px.get("trade_levels")
    if isinstance(tl, dict) and tl:
        return dict(tl)
    ent = px.get("entry") or {}
    risk = px.get("risk") or {}
    pat = px.get("pattern") or {}
    pat_name = pat.get("pattern_name") if pat else None
    if pat_name is None and px.get("signal"):
        pat_name = "None"
    return {
        "entry_price": ent.get("entry_price"),
        "target_1": risk.get("target_1"),
        "target_2": risk.get("target_2"),
        "stop_price": risk.get("stop_price"),
        "exit_price": None,
        "pattern_name": pat_name,
        "pattern_breakout": bool(pat.get("confirmed")) if pat else False,
        "notes": (
            "exit_price is null until backtest or execution merge; "
            "prefer phoenix.trade_levels when present."
        ),
    }


def _direction_to_phoenix_signal(direction: Optional[str]) -> Optional[str]:
    """Fusion/phoenix direction strings → BUY / WATCH / AVOID for bundle counts."""
    d = (direction or "").lower()
    if d == "bullish":
        return "BUY"
    if d == "bearish":
        return "AVOID"
    if d == "neutral":
        return "WATCH"
    return None


def row_from_labeled_backtest_period(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    period: Dict[str, Any],
    artifact_name: str,
) -> Dict[str, Any]:
    """
    One row per Phoenix+FA backtest period with TP/FP-style labels when available.

    ``period`` should match :mod:`agents.orchestrator.backtest_phoenix` period dicts.
    """
    tl = period.get("trade_levels")
    if isinstance(tl, dict):
        tl_out = dict(tl)
    else:
        tl_out = {}
    px_dir = period.get("phoenix_signal")
    phx_sym = _direction_to_phoenix_signal(px_dir)
    sc = period.get("signal_correct")
    err = period.get("error")
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": "phoenix-fa",
        "fusion_final_signal": period.get("signal"),
        "fusion_orchestrator_score": period.get("orchestrator_score"),
        "fusion_conflict": period.get("conflict_detected"),
        "phoenix_signal": phx_sym,
        "phoenix_score": period.get("phoenix_score"),
        "fund_signal_normalized": None,
        "fund_score": period.get("fund_score"),
        "hard_filter_passed": None,
        "trade_levels": tl_out,
        "backtest": {
            "signal_date": period.get("signal_date"),
            "result_date": period.get("result_date"),
            "entry_price": period.get("start_price"),
            "exit_reference_price": period.get("exit_reference_price"),
            "exit_reference_date": period.get("exit_reference_date"),
            "target_price": period.get("target_price"),
            "target_hit": period.get("target_hit"),
            "target_hit_date": period.get("target_hit_date"),
        },
        "artifact_relative": artifact_name,
        "error": err,
        "evaluation": {
            "directional_labels_available": sc is not None,
            "signal_correct": sc,
            "notes": (
                "Labeled backtest row: signal_correct from target-hit vs fusion signal "
                "(see agents/orchestrator/backtest_phoenix). Inputs use data through "
                "as_of_date only; exit_reference_* uses forward window."
            ),
        },
    }


def row_from_phoenix_fund(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    payload: Dict[str, Any],
    artifact_name: str,
) -> Dict[str, Any]:
    fus = payload.get("fusion") or {}
    px = payload.get("phoenix") or {}
    fund = payload.get("fundamental") or {}
    fsig, fscore = _fund_signal_from_eval(fund)
    tl = trade_levels_from_phoenix(px)
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": "phoenix-fa",
        "fusion_final_signal": fus.get("final_signal"),
        "fusion_orchestrator_score": fus.get("orchestrator_score"),
        "fusion_conflict": fus.get("conflict_detected"),
        "phoenix_signal": (px.get("signal") or "").upper() or None,
        "phoenix_score": px.get("score"),
        "fund_signal_normalized": fsig,
        "fund_score": fscore,
        "hard_filter_passed": px.get("hard_filter_passed"),
        "trade_levels": tl,
        "artifact_relative": artifact_name,
        "error": None,
        "evaluation": {
            "directional_labels_available": False,
            "signal_correct": None,
            "notes": (
                "TP/FP/TN/FN require forward outcomes from a backtest merge; "
                "see matrices.signal_distribution for this run only."
            ),
        },
    }


def row_from_ta_fa(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    result: Dict[str, Any],
    artifact_name: str,
) -> Dict[str, Any]:
    tech = result.get("tech_output") or {}
    fund = result.get("fund_output") or {}
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": "ta-fa",
        "fusion_final_signal": result.get("final_signal"),
        "fusion_orchestrator_score": result.get("orchestrator_score"),
        "fusion_conflict": result.get("conflict_detected"),
        "tech_score": tech.get("score"),
        "fund_score": fund.get("score"),
        "phoenix_signal": None,
        "phoenix_score": None,
        "fund_signal_normalized": None,
        "hard_filter_passed": None,
        "artifact_relative": artifact_name,
        "error": None,
        "evaluation": {
            "directional_labels_available": False,
            "signal_correct": None,
            "notes": None,
        },
    }


def row_from_compare(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    orch: Dict[str, Any],
    px: Dict[str, Any],
    artifact_ta: str,
    artifact_px: str,
) -> Dict[str, Any]:
    """Side-by-side TA+FA orchestrator vs Phoenix-only artifacts."""
    tech = orch.get("tech_output") or {} if orch else {}
    fund = orch.get("fund_output") or {} if orch else {}
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": "compare",
        "fusion_final_signal": orch.get("final_signal") if orch else None,
        "fusion_orchestrator_score": orch.get("orchestrator_score") if orch else None,
        "fusion_conflict": orch.get("conflict_detected") if orch else None,
        "tech_score": tech.get("score"),
        "fund_score": fund.get("score"),
        "phoenix_signal": ((px.get("signal") or "").upper() or None) if px else None,
        "phoenix_score": px.get("score") if px else None,
        "fund_signal_normalized": None,
        "hard_filter_passed": px.get("hard_filter_passed") if px else None,
        "artifacts": {"ta_fa": artifact_ta, "phoenix": artifact_px},
        "artifact_relative": artifact_ta,
        "error": None,
        "evaluation": {"directional_labels_available": False, "signal_correct": None, "notes": None},
    }


def row_from_phoenix_only(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    px: Dict[str, Any],
    artifact_name: str,
) -> Dict[str, Any]:
    tl = trade_levels_from_phoenix(px)
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": "phoenix",
        "fusion_final_signal": None,
        "fusion_orchestrator_score": None,
        "fusion_conflict": None,
        "phoenix_signal": (px.get("signal") or "").upper() or None,
        "phoenix_score": px.get("score"),
        "fund_signal_normalized": None,
        "fund_score": None,
        "hard_filter_passed": px.get("hard_filter_passed"),
        "trade_levels": tl,
        "artifact_relative": artifact_name,
        "error": None,
        "evaluation": {"directional_labels_available": False, "signal_correct": None, "notes": None},
    }


def row_from_error(
    ticker: str,
    as_of_date: str,
    sector: Optional[str],
    fusion_mode: str,
    err: str,
) -> Dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "sector": sector,
        "as_of_date": as_of_date,
        "fusion_mode": fusion_mode,
        "fusion_final_signal": None,
        "fusion_orchestrator_score": None,
        "fusion_conflict": None,
        "phoenix_signal": None,
        "phoenix_score": None,
        "fund_signal_normalized": None,
        "fund_score": None,
        "hard_filter_passed": None,
        "artifact_relative": None,
        "error": err,
        "evaluation": {"directional_labels_available": False, "signal_correct": None, "notes": None},
    }


def compute_matrices(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Signal alignment tables (not TP/FP unless evaluation.signal_correct is set)."""
    fusion_counts: Dict[str, int] = {"bullish": 0, "neutral": 0, "bearish": 0}
    px_counts: Dict[str, int] = {"BUY": 0, "WATCH": 0, "AVOID": 0}
    cross_fp: Dict[str, Dict[str, int]] = {
        "bullish": {"bullish": 0, "neutral": 0, "bearish": 0},
        "neutral": {"bullish": 0, "neutral": 0, "bearish": 0},
        "bearish": {"bullish": 0, "neutral": 0, "bearish": 0},
    }

    confusion_ready = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "neutral": 0, "skipped": 0}

    for r in rows:
        if r.get("error"):
            continue
        fs = r.get("fusion_final_signal")
        if fs in fusion_counts:
            fusion_counts[fs] += 1

        ps = r.get("phoenix_signal")
        if ps in px_counts:
            px_counts[ps] += 1

        if fs in cross_fp and ps is not None:
            pd = _phoenix_direction(ps)
            if pd in cross_fp[fs]:
                cross_fp[fs][pd] += 1

        ev = r.get("evaluation") or {}
        sc = ev.get("signal_correct")
        fus_sig = r.get("fusion_final_signal")
        if sc is True or sc is False:
            # Minimal TP/FP/TN/FN when merge pipeline fills evaluation
            pred_bull = fus_sig == "bullish"
            if fus_sig == "neutral":
                confusion_ready["neutral"] += 1
            elif pred_bull:
                confusion_ready["TP" if sc else "FP"] += 1
            else:
                confusion_ready["TN" if sc else "FN"] += 1
        else:
            confusion_ready["skipped"] += 1

    return {
        "fusion_signal_counts": fusion_counts,
        "phoenix_signal_counts": px_counts,
        "cross_tab_fusion_vs_phoenix_direction": cross_fp,
        "confusion_when_labeled": confusion_ready,
        "description": (
            "cross_tab rows=fusion (CWAF), cols=Phoenix mapped to bullish/neutral/bearish. "
            "Traditional confusion matrix counts populate only when rows[].evaluation.signal_correct is set."
        ),
    }


def build_run_bundle(
    *,
    run_id: str,
    as_of_date: str,
    fusion: str,
    universe_label: str,
    fund_data_source: str,
    rows: List[Dict[str, Any]],
    halal_universe_mode: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at_utc": _utc_now_iso(),
        "as_of_date": as_of_date,
        "fusion": fusion,
        "fund_data_source": fund_data_source,
        "universe": {
            "description": universe_label,
            "halal_universe": halal_universe_mode,
        },
        "row_count": len(rows),
        "rows": rows,
        "matrices": compute_matrices(rows),
    }


def write_bundle(out_dir: Path, bundle: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "run_bundle.json"
    path.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return path


def load_bundle(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_bundles(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Delta keyed by ticker (uppercase); stable for UI."""
    rows_a = {str(r["ticker"]).upper(): r for r in a.get("rows") or []}
    rows_b = {str(r["ticker"]).upper(): r for r in b.get("rows") or []}
    tickers = sorted(set(rows_a) | set(rows_b))

    per_ticker: Dict[str, Any] = {}
    for t in tickers:
        ra, rb = rows_a.get(t), rows_b.get(t)
        if ra is None:
            per_ticker[t] = {"status": "added_in_b", "row_b": rb}
            continue
        if rb is None:
            per_ticker[t] = {"status": "removed_in_b", "row_a": ra}
            continue
        delta_score = None
        try:
            sa = ra.get("fusion_orchestrator_score")
            sb = rb.get("fusion_orchestrator_score")
            if sa is not None and sb is not None:
                delta_score = round(float(sb) - float(sa), 4)
        except (TypeError, ValueError):
            pass
        per_ticker[t] = {
            "status": "both",
            "fusion_signal": {"from": ra.get("fusion_final_signal"), "to": rb.get("fusion_final_signal")},
            "phoenix_signal": {"from": ra.get("phoenix_signal"), "to": rb.get("phoenix_signal")},
            "fusion_score_delta": delta_score,
            "changed": (
                ra.get("fusion_final_signal") != rb.get("fusion_final_signal")
                or ra.get("phoenix_signal") != rb.get("phoenix_signal")
                or (delta_score is not None and abs(delta_score) > 1e-6)
            ),
        }

    summary = {
        "tickers_compared": len(tickers),
        "signal_changes": sum(
            1
            for k, v in per_ticker.items()
            if isinstance(v, dict)
            and v.get("status") == "both"
            and v.get("changed")
        ),
        "added": sum(1 for v in per_ticker.values() if v.get("status") == "added_in_b"),
        "removed": sum(1 for v in per_ticker.values() if v.get("status") == "removed_in_b"),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "comparison_id": str(uuid.uuid4()),
        "created_at_utc": _utc_now_iso(),
        "run_a": {"run_id": a.get("run_id"), "as_of_date": a.get("as_of_date"), "fusion": a.get("fusion")},
        "run_b": {"run_id": b.get("run_id"), "as_of_date": b.get("as_of_date"), "fusion": b.get("fusion")},
        "summary": summary,
        "per_ticker": per_ticker,
    }


def write_compare(out_path: Path, cmp: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cmp, indent=2, default=str), encoding="utf-8")
