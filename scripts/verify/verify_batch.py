#!/usr/bin/env python3
"""
Batch-verify backtest artifacts and maintain a dashboard index.

Example::

    python scripts/verify/verify_batch.py \\
        --glob "sector_information-technology_*" \\
        --rate-limit 2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERIFY_DIR = ROOT / "data" / "output" / "verify"
RUNS_DIR = ROOT / "data" / "output" / "trading_runs"
INDEX_PATH = VERIFY_DIR / "verify_index.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _signal_date_from_dir(name: str) -> str | None:
    m = re.search(r"_(\d{4}-\d{2}-\d{2})$", name)
    return m.group(1) if m else None


def discover_artifacts(glob_pattern: str) -> list[Path]:
    if not RUNS_DIR.is_dir():
        return []
    out: list[Path] = []
    for d in sorted(RUNS_DIR.iterdir()):
        if not d.is_dir():
            continue
        if glob_pattern and not d.match(glob_pattern):
            continue
        master = d / "master_pilot.json"
        if master.is_file():
            out.append(master)
    return out


def _index_entry(artifact: Path, report_path: Path | None) -> dict:
    folder = artifact.parent.name
    signal_date = _signal_date_from_dir(folder) or ""
    entry: dict = {
        "signal_date": signal_date,
        "folder": folder,
        "artifact_rel": str(artifact.relative_to(ROOT)),
        "report_rel": str(report_path.relative_to(ROOT)) if report_path and report_path.is_file() else None,
        "verified": report_path.is_file() if report_path else False,
    }
    if report_path and report_path.is_file():
        try:
            doc = json.loads(report_path.read_text(encoding="utf-8"))
            vs = doc.get("verified_summary") or (doc.get("meta") or {}).get("verified_summary") or {}
            sm = doc.get("summary") or {}
            ac = vs.get("artifact_claimed") or {}
            pv = vs.get("polygon_verified") or {}
            manifests = (doc.get("meta") or {}).get("artifacts") or []
            ticker_count = None
            if manifests and isinstance(manifests[0], dict):
                ticker_count = manifests[0].get("tickers_requested")
            entry.update(
                {
                    "verified_at": (doc.get("meta") or {}).get("verified_at"),
                    "ticker_count": ticker_count,
                    "rows_total": sm.get("rows_total"),
                    "rows_pass": sm.get("rows_pass"),
                    "rows_fail": sm.get("rows_fail"),
                    "rows_skip": sm.get("rows_skip"),
                    "pass_rate_pct": sm.get("pass_rate_pct"),
                    "artifact_tp": ac.get("bullish_tp"),
                    "artifact_fp": ac.get("bullish_fp"),
                    "confirmed_tp": pv.get("confirmed_tp"),
                    "disputed_tp": pv.get("disputed_tp"),
                    "confirmed_fp": pv.get("confirmed_fp"),
                    "disputed_fp": pv.get("disputed_fp"),
                    "tp_confirmation_rate_pct": pv.get("tp_confirmation_rate_pct"),
                }
            )
        except Exception as exc:
            entry["parse_error"] = str(exc)
    return entry


def build_index(artifacts: list[Path]) -> dict:
    runs = []
    for art in artifacts:
        report = VERIFY_DIR / f"{art.parent.name}_verify_report.json"
        runs.append(_index_entry(art, report))
    runs.sort(key=lambda r: r.get("signal_date") or "", reverse=True)

    verified = [r for r in runs if r.get("verified")]
    agg = {
        "total_artifacts": len(runs),
        "verified_count": len(verified),
        "missing_count": len(runs) - len(verified),
        "total_artifact_tp": sum(r.get("artifact_tp") or 0 for r in verified),
        "total_confirmed_tp": sum(r.get("confirmed_tp") or 0 for r in verified),
        "total_disputed_tp": sum(r.get("disputed_tp") or 0 for r in verified),
        "total_rows_pass": sum(r.get("rows_pass") or 0 for r in verified),
        "total_rows_fail": sum(r.get("rows_fail") or 0 for r in verified),
    }
    if agg["total_artifact_tp"]:
        agg["overall_tp_confirmation_rate_pct"] = round(
            agg["total_confirmed_tp"] / agg["total_artifact_tp"] * 100, 1
        )
    else:
        agg["overall_tp_confirmation_rate_pct"] = None

    return {"updated_at": _utc_now(), "runs": runs, "aggregate": agg}


def write_index(index: dict) -> None:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch-verify backtest master_pilot artifacts.")
    parser.add_argument(
        "--glob",
        default="sector_information-technology_*",
        help="Folder glob under trading_runs (default: IT sector sweep)",
    )
    parser.add_argument("--rate-limit", type=float, default=2.0)
    parser.add_argument("--force", action="store_true", help="Re-verify even if report exists")
    parser.add_argument("--index-only", action="store_true", help="Rebuild index without verifying")
    args = parser.parse_args(argv)

    artifacts = discover_artifacts(args.glob)
    if not artifacts:
        print(f"No artifacts matching {args.glob!r} under {RUNS_DIR}", file=sys.stderr)
        return 1

    if args.index_only:
        index = build_index(artifacts)
        write_index(index)
        print(f"Index written → {INDEX_PATH} ({len(artifacts)} artifacts)")
        return 0

    os.environ.setdefault("POLYGON_REQUESTS_PER_SECOND", str(args.rate_limit))
    from scripts.verify.runner import run_verification

    t0 = time.time()
    results: list[dict] = []
    for i, art in enumerate(artifacts, 1):
        report_path = VERIFY_DIR / f"{art.parent.name}_verify_report.json"
        if not args.force and report_path.is_file():
            print(f"[{i}/{len(artifacts)}] SKIP (exists) {art.parent.name}")
            results.append({"folder": art.parent.name, "status": "skipped"})
            continue

        print(f"[{i}/{len(artifacts)}] VERIFY {art.parent.name} …", flush=True)
        try:
            report = run_verification(
                art,
                dry_run=False,
                tolerance_abs=0.01,
                tolerance_rel=0.0001,
            )
            report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            sm = report.summary
            vs = report.meta.get("verified_summary") or {}
            pv = vs.get("polygon_verified") or {}
            print(
                f"    pass={sm.get('rows_pass')} fail={sm.get('rows_fail')} skip={sm.get('rows_skip')} "
                f"TP={pv.get('confirmed_tp')}/{vs.get('artifact_claimed', {}).get('bullish_tp')}",
                flush=True,
            )
            results.append({"folder": art.parent.name, "status": "ok", "summary": sm})
        except Exception as exc:
            print(f"    ERROR: {exc}", flush=True)
            results.append({"folder": art.parent.name, "status": "error", "error": str(exc)})

    index = build_index(artifacts)
    write_index(index)
    elapsed = time.time() - t0
    print()
    print("=" * 72)
    print(f"Batch done in {elapsed:.0f}s — {len(artifacts)} artifacts")
    print(f"Index → {INDEX_PATH}")
    print(f"Aggregate: {index['aggregate']}")
    print("=" * 72)
    errors = [r for r in results if r.get("status") == "error"]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
