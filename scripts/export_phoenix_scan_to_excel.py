#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def _validate_date_iso(d: str) -> str:
    datetime.strptime(d, "%Y-%m-%d")
    return d


def _safe_get(d: Optional[Dict[str, Any]], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _as_num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x))
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a Phoenix sector scan JSON to Excel (with full report text)."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Scan cutoff date folder (YYYY-MM-DD), e.g. 2026-04-30",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Optional explicit path to phoenix_sector_scan_<date>.json (overrides --date).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output xlsx path. Default: alongside the JSON.",
    )
    args = parser.parse_args()

    scan_date = _validate_date_iso(args.date)

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    if args.input:
        in_path = Path(args.input).expanduser().resolve()
    else:
        in_path = (
            root
            / "data"
            / "output"
            / "phoenix_sector_scans"
            / scan_date
            / f"phoenix_sector_scan_{scan_date}.json"
        )

    payload = json.loads(in_path.read_text())
    meta = payload.get("meta") or {}
    results: List[Dict[str, Any]] = payload.get("results") or []

    rows: List[Dict[str, Any]] = []
    for r in results:
        signal = str(r.get("signal") or "")
        buy_and_watch = signal in {"BUY", "WATCH"}

        stage = r.get("stage") or {}
        pattern = r.get("pattern") or {}
        entry = r.get("entry") or {}
        risk = r.get("risk") or {}

        # "Detailed column" equivalent to the UI popup text
        report = r.get("report") or ""

        rows.append(
            {
                "as_of_date": r.get("as_of_date"),
                "sector": r.get("sector"),
                "ticker": r.get("ticker"),
                "signal": signal,
                "buy_and_watch": "YES" if buy_and_watch else "NO",
                "score": _as_num(r.get("score")),
                "hard_filter_passed": bool(r.get("hard_filter_passed")),
                "hard_filter_reason": r.get("hard_filter_reason"),
                "stage_num": _safe_get(stage, "stage"),
                "stage_label": _safe_get(stage, "label"),
                "stage_action": _safe_get(stage, "action"),
                "pattern_name": _safe_get(pattern, "pattern_name"),
                "pattern_confirmed": _safe_get(pattern, "confirmed"),
                "pattern_volume_confirmed": _safe_get(pattern, "volume_confirmed"),
                "pattern_confidence": _as_num(_safe_get(pattern, "confidence")),
                "entry_type": _safe_get(entry, "entry_type"),
                "entry_price": _as_num(_safe_get(entry, "entry_price")),
                "entry_trigger": _safe_get(entry, "trigger_description"),
                # Phoenix does not backtest an "exit" here; these are setup risk levels at cutoff.
                "stop_price": _as_num(_safe_get(risk, "stop_price")),
                "stop_pct": _as_num(_safe_get(risk, "stop_pct")),
                "target_1": _as_num(_safe_get(risk, "target_1")),
                "target_2": _as_num(_safe_get(risk, "target_2")),
                "reward_risk": _as_num(_safe_get(risk, "reward_risk")),
                "position_size_shares": _as_num(_safe_get(risk, "position_size_shares")),
                "trail_stop_ma": _safe_get(risk, "trail_stop_ma"),
                "warnings": " | ".join((r.get("warnings") or [])),
                "details_report": report,
            }
        )

    df = pd.DataFrame(rows)
    # Nice ordering
    if not df.empty:
        df = df.sort_values(by=["sector", "signal", "score", "ticker"], ascending=[True, True, False, True])

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        out_path = in_path.with_suffix(".xlsx")

    # Create an Excel workbook with a compact Summary sheet and a full Data sheet
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary_cols = [
            "as_of_date",
            "sector",
            "ticker",
            "signal",
            "buy_and_watch",
            "score",
            "hard_filter_passed",
            "stage_num",
            "stage_label",
            "pattern_name",
            "pattern_confirmed",
            "entry_type",
            "entry_price",
            "stop_price",
            "target_1",
            "target_2",
            "reward_risk",
        ]
        df[summary_cols].to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="Full", index=False)

        # Meta sheet
        meta_df = pd.DataFrame(
            [
                {"key": "as_of_date", "value": meta.get("as_of_date")},
                {"key": "sectors", "value": ", ".join(meta.get("sectors") or [])},
                {"key": "tickers_requested", "value": meta.get("tickers_requested")},
                {"key": "results", "value": meta.get("results")},
                {"key": "errors", "value": meta.get("errors")},
                {"key": "workers", "value": meta.get("workers")},
                {"key": "elapsed_sec", "value": meta.get("elapsed_sec")},
                {"key": "generated_at", "value": meta.get("generated_at")},
                {"key": "source_json", "value": str(in_path)},
            ]
        )
        meta_df.to_excel(writer, sheet_name="Meta", index=False)

        # Autofit-ish widths for Summary + Meta (Full can be huge due to report column)
        for sheet_name in ("Summary", "Meta"):
            ws = writer.book[sheet_name]
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col[:2000]:
                    try:
                        v = "" if cell.value is None else str(cell.value)
                        max_len = max(max_len, len(v))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(60, max(10, max_len + 2))

    print("Wrote:", str(out_path))


if __name__ == "__main__":
    main()

