"""Orchestrate loading, Polygon re-fetch, and diff reporting."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .artifact_loader import load_verify_rows
from .diff_report import build_summary, verify_row
from .models import RowVerification, VerifyReport
from .polygon_checks import PolygonVerifier


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_verification(
    input_path: Path,
    *,
    dry_run: bool = False,
    sample: Optional[int] = None,
    seed: int = 42,
    tolerance_abs: float = 0.01,
    tolerance_rel: float = 0.0001,
    fields: Optional[Set[str]] = None,
    fail_fast: bool = False,
) -> VerifyReport:
    rows, manifests = load_verify_rows(input_path)

    if sample is not None and sample > 0 and sample < len(rows):
        rng = random.Random(seed)
        rows = rng.sample(rows, sample)

    meta: Dict[str, Any] = {
        "input": str(input_path.resolve()),
        "verified_at": _utc_now(),
        "dry_run": dry_run,
        "artifacts": manifests,
        "rows_requested": len(rows),
        "sample_size": sample,
        "tolerance_abs": tolerance_abs,
        "tolerance_rel": tolerance_rel,
        "fields": sorted(fields) if fields else ["prices", "target_hit", "labels", "dates"],
    }

    if dry_run:
        return VerifyReport(
            meta=meta,
            summary={
                "rows_total": len(rows),
                "rows_pass": 0,
                "rows_fail": 0,
                "rows_skip": len(rows),
                "dry_run": True,
            },
            rows=[],
        )

    from agents.polygon_data import PolygonClient

    client = PolygonClient()
    verifier = PolygonVerifier(client)
    results: List[RowVerification] = []

    for row in rows:
        recomputed = verifier.recompute_row(row)
        rv = verify_row(
            row,
            recomputed,
            tol_abs=tolerance_abs,
            tol_rel=tolerance_rel,
            fields=fields,
        )
        results.append(rv)
        if fail_fast and rv.status == "FAIL":
            break

    summary = build_summary(results)
    summary["polygon_available"] = client.is_available()
    summary["unique_tickers"] = len({r.row.ticker for r in results})

    from .verified_summary import build_verified_summary

    verified_summary = build_verified_summary(results)

    meta["verified_summary"] = verified_summary

    return VerifyReport(meta=meta, summary=summary, rows=results)


def print_console_summary(report: VerifyReport) -> None:
    s = report.summary
    print()
    print("=" * 72)
    print("Backtest verification summary (audit-only)")
    print("=" * 72)
    print(f"Input:     {report.meta.get('input')}")
    print(f"Verified:  {report.meta.get('verified_at')}")
    print(f"Rows:      {s.get('rows_total', 0)} total | {s.get('rows_pass', 0)} pass | "
          f"{s.get('rows_fail', 0)} fail | {s.get('rows_skip', 0)} skip")
    if s.get("pass_rate_pct") is not None:
        print(f"Pass rate: {s.get('pass_rate_pct')}% (excluding skips)")
    vs = report.meta.get("verified_summary") or {}
    av = vs.get("artifact_claimed") or {}
    pv = vs.get("polygon_verified") or {}
    if av.get("bullish_tp") is not None:
        print(
            f"Verified TP: {pv.get('confirmed_tp', 0)}/{av.get('bullish_tp', 0)} bullish winners confirmed "
            f"({pv.get('tp_confirmation_rate_pct')}% ) · disputed: {pv.get('disputed_tp', 0)}"
        )
    mismatches = s.get("mismatch_by_field") or {}
    if mismatches:
        print("Mismatches by field:")
        for fld, cnt in sorted(mismatches.items(), key=lambda x: -x[1]):
            print(f"  {fld}: {cnt}")
    fails = [r for r in report.rows if r.status == "FAIL"]
    if fails:
        print()
        print("First failures:")
        for rv in fails[:10]:
            print(f"  {rv.row.ticker} @ {rv.row.signal_date}:")
            for chk in rv.checks:
                if chk.status == "FAIL":
                    print(f"    {chk.field}: expected={chk.expected!r} actual={chk.actual!r}")
    print("=" * 72)
