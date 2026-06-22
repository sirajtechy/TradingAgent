"""Load and normalize backtest artifacts into VerifyRow objects."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import VerifyRow


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _infer_result_date(manifest: Dict[str, Any], signal_date: str) -> Optional[str]:
    rd = manifest.get("result_date")
    if rd:
        return str(rd)[:10]
    eval_days = manifest.get("eval_days")
    if eval_days is not None:
        try:
            sig = date.fromisoformat(signal_date[:10])
            return (sig + timedelta(days=int(eval_days))).isoformat()
        except (TypeError, ValueError):
            pass
    return None


def _row_from_period(
    ticker: str,
    period: Dict[str, Any],
    source: str,
    default_signal_date: Optional[str] = None,
    default_result_date: Optional[str] = None,
) -> VerifyRow:
    sig = str(period.get("signal_date") or default_signal_date or "")[:10]
    res = str(period.get("result_date") or default_result_date or "")[:10]
    return VerifyRow(
        ticker=ticker.upper(),
        signal_date=sig,
        result_date=res,
        entry_price=_safe_float(period.get("start_price")),
        start_price_date=period.get("start_price_date"),
        exit_reference_price=_safe_float(period.get("exit_reference_price")),
        exit_reference_date=period.get("exit_reference_date"),
        target_price=_safe_float(period.get("target_price")),
        target_hit=period.get("target_hit") if period.get("target_hit") is not None else None,
        target_hit_date=period.get("target_hit_date"),
        fusion_final_signal=period.get("signal"),
        technical_signal=period.get("technical_signal"),
        phoenix_signal=period.get("phoenix_signal"),
        signal_correct=period.get("signal_correct"),
        signal_correct_technical=period.get("signal_correct_technical"),
        signal_correct_phoenix=period.get("signal_correct_phoenix"),
        error=period.get("error"),
        source_artifact=source,
    )


def _row_from_master_ticker(
    ticker: str,
    row: Dict[str, Any],
    manifest: Dict[str, Any],
    source: str,
) -> VerifyRow:
    signal_date = str(manifest.get("signal_date") or "")[:10]
    result_date = _infer_result_date(manifest, signal_date) or ""
    return VerifyRow(
        ticker=ticker.upper(),
        signal_date=signal_date,
        result_date=result_date,
        entry_price=_safe_float(row.get("entry_price")),
        start_price_date=None,
        exit_reference_price=_safe_float(row.get("exit_price")),
        exit_reference_date=row.get("exit_reference_date"),
        target_price=_safe_float(row.get("backtest_target_price") or row.get("target_t1")),
        target_hit=row.get("target_hit") if row.get("target_hit") is not None else None,
        target_hit_date=row.get("target_hit_date"),
        fusion_final_signal=row.get("fusion_final_signal"),
        technical_signal=row.get("technical_signal"),
        phoenix_signal=row.get("phoenix_signal_directional") or row.get("phoenix_signal"),
        signal_correct=row.get("signal_correct"),
        signal_correct_technical=row.get("signal_correct_technical"),
        signal_correct_phoenix=row.get("signal_correct_phoenix"),
        error=row.get("error"),
        source_artifact=source,
    )


def _row_from_bundle(
    row: Dict[str, Any],
    manifest: Dict[str, Any],
    source: str,
) -> VerifyRow:
    bt = row.get("backtest") or {}
    ev = row.get("evaluation") or {}
    signal_date = str(bt.get("signal_date") or manifest.get("signal_date") or "")[:10]
    result_date = str(bt.get("result_date") or _infer_result_date(manifest, signal_date) or "")[:10]
    tl = row.get("trade_levels") or {}
    entry = _safe_float(bt.get("entry_price"))
    if entry is None:
        entry = _safe_float(tl.get("entry_price"))
    target = _safe_float(bt.get("target_price"))
    if target is None:
        target = _safe_float(tl.get("target_1"))
    return VerifyRow(
        ticker=str(row.get("ticker") or "").upper(),
        signal_date=signal_date,
        result_date=result_date,
        entry_price=entry,
        start_price_date=None,
        exit_reference_price=_safe_float(bt.get("exit_reference_price")),
        exit_reference_date=bt.get("exit_reference_date"),
        target_price=target,
        target_hit=bt.get("target_hit") if bt.get("target_hit") is not None else None,
        target_hit_date=bt.get("target_hit_date"),
        fusion_final_signal=row.get("fusion_final_signal"),
        technical_signal=row.get("technical_signal"),
        phoenix_signal=row.get("phoenix_signal"),
        signal_correct=ev.get("signal_correct"),
        signal_correct_technical=ev.get("signal_correct_technical"),
        signal_correct_phoenix=None,
        error=row.get("error"),
        source_artifact=source,
    )


def detect_artifact_type(data: Dict[str, Any], path: Path) -> str:
    name = path.name.lower()
    if name == "master_pilot.json" or ("tickers" in data and "manifest" in data):
        return "master_pilot"
    if name == "pilot_results.json" or ("results" in data and isinstance(data.get("results"), dict)):
        return "pilot_results"
    if name == "run_bundle.json" or ("rows" in data and "run_id" in data):
        return "run_bundle"
    if "periods" in data and "ticker" in data:
        return "single_ticker"
    raise ValueError(f"Unrecognized artifact format: {path}")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows_from_artifact(path: Path) -> Tuple[List[VerifyRow], Dict[str, Any]]:
    """Parse one artifact file into normalized rows + manifest metadata."""
    data = _load_json(path)
    artifact_type = detect_artifact_type(data, path)
    source = str(path)
    manifest: Dict[str, Any] = data.get("manifest") or data.get("pilot_meta") or {}
    rows: List[VerifyRow] = []

    if artifact_type == "master_pilot":
        tickers = data.get("tickers") or {}
        for sym, trow in tickers.items():
            if isinstance(trow, dict):
                rows.append(_row_from_master_ticker(str(sym), trow, manifest, source))

    elif artifact_type == "pilot_results":
        results = data.get("results") or {}
        for sym, payload in results.items():
            if not isinstance(payload, dict):
                continue
            if payload.get("error") and not payload.get("periods"):
                rows.append(
                    VerifyRow(
                        ticker=str(sym).upper(),
                        signal_date=str(manifest.get("signal_date") or "")[:10],
                        result_date=_infer_result_date(manifest, str(manifest.get("signal_date") or "")) or "",
                        error=str(payload.get("error")),
                        source_artifact=source,
                    )
                )
                continue
            for period in payload.get("periods") or []:
                if isinstance(period, dict):
                    rows.append(
                        _row_from_period(
                            str(sym),
                            period,
                            source,
                            default_signal_date=str(manifest.get("signal_date") or "")[:10],
                            default_result_date=_infer_result_date(
                                manifest, str(manifest.get("signal_date") or "")
                            ),
                        )
                    )

    elif artifact_type == "run_bundle":
        manifest = data.get("pilot_meta") or manifest
        for row in data.get("rows") or []:
            if isinstance(row, dict):
                rows.append(_row_from_bundle(row, manifest, source))

    elif artifact_type == "single_ticker":
        ticker = str(data.get("ticker") or path.stem.split("_")[0]).upper()
        for period in data.get("periods") or []:
            if isinstance(period, dict):
                rows.append(_row_from_period(ticker, period, source))

    if not manifest.get("signal_date") and rows:
        manifest.setdefault("signal_date", rows[0].signal_date)
    if not manifest.get("result_date") and rows and rows[0].result_date:
        manifest.setdefault("result_date", rows[0].result_date)

    return rows, manifest


def discover_artifacts(input_path: Path) -> List[Path]:
    """Resolve a file or directory to a list of verifiable artifact paths."""
    p = Path(input_path)
    if p.is_file():
        return [p.resolve()]
    if not p.is_dir():
        raise FileNotFoundError(f"Input not found: {p}")

    patterns = ("master_pilot.json", "pilot_results.json", "run_bundle.json")
    found: List[Path] = []
    for name in patterns:
        found.extend(sorted(p.rglob(name)))
    if found:
        # Prefer master_pilot when multiple formats exist in same folder
        by_dir: Dict[Path, List[Path]] = {}
        for f in found:
            by_dir.setdefault(f.parent, []).append(f)
        out: List[Path] = []
        for d, files in sorted(by_dir.items()):
            masters = [f for f in files if f.name == "master_pilot.json"]
            if masters:
                out.append(masters[0])
            else:
                out.extend(files)
        return out

    raise FileNotFoundError(
        f"No verifiable artifacts under {p} (expected master_pilot.json, pilot_results.json, or run_bundle.json)"
    )


def load_verify_rows(input_path: Path) -> Tuple[List[VerifyRow], List[Dict[str, Any]]]:
    """
    Load all rows from a file or directory tree.

    Returns (rows, manifests) where manifests has one entry per artifact file.
    """
    artifacts = discover_artifacts(input_path)
    all_rows: List[VerifyRow] = []
    manifests: List[Dict[str, Any]] = []
    for art in artifacts:
        rows, manifest = load_rows_from_artifact(art)
        manifest = dict(manifest)
        manifest["artifact_path"] = str(art)
        manifests.append(manifest)
        all_rows.extend(rows)
    return all_rows, manifests
