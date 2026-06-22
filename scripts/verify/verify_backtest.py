#!/usr/bin/env python3
"""
verify_backtest.py — Audit-only backtest output verification against Polygon.

Reads finished backtest artifacts (master_pilot.json, pilot_results.json, run_bundle.json),
re-fetches Polygon bars independently, and reports mismatches on price/outcome fields.

This tool is NOT wired into the backtest pipeline. Run it after a backtest completes,
preferably when no other Polygon-heavy job is running.

Example::

    cd MyTradingSpace
    set -a && source .env && set +a
    python scripts/verify/verify_backtest.py \\
        --input data/output/trading_runs/sector_information-technology_2025-04-02/master_pilot.json \\
        --rate-limit 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT_DIR = ROOT / "data" / "output" / "verify"


def _parse_fields(raw: str) -> set[str]:
    allowed = {"prices", "target_hit", "labels", "dates"}
    parts = {p.strip().lower() for p in raw.split(",") if p.strip()}
    bad = parts - allowed
    if bad:
        raise SystemExit(f"Unknown --fields values: {', '.join(sorted(bad))}. Allowed: {', '.join(sorted(allowed))}")
    return parts or allowed


def _default_output_path(input_path: Path) -> Path:
    stem = input_path.stem if input_path.is_file() else input_path.name
    parent_name = input_path.parent.name if input_path.is_file() else stem
    return DEFAULT_OUTPUT_DIR / f"{parent_name}_verify_report.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Verify backtest Polygon price/outcome fields against independent API fetch (audit-only).",
    )
    p.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Artifact file or directory (searches for master_pilot.json, pilot_results.json, run_bundle.json)",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=f"Report JSON path (default: {DEFAULT_OUTPUT_DIR}/<run>_verify_report.json)",
    )
    p.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Polygon requests/sec cap for this verifier run (default: 2)",
    )
    p.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Absolute price tolerance in dollars (default: 0.01)",
    )
    p.add_argument(
        "--tolerance-rel",
        type=float,
        default=0.0001,
        help="Relative price tolerance as fraction (default: 0.0001 = 0.01%%)",
    )
    p.add_argument(
        "--fields",
        default="prices,target_hit,labels,dates",
        help="Comma-separated check groups: prices, target_hit, labels, dates",
    )
    p.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Randomly verify N rows only (spot-check mode)",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed for --sample")
    p.add_argument("--dry-run", action="store_true", help="Parse artifacts only; no Polygon calls")
    p.add_argument("--fail-fast", action="store_true", help="Stop after first failing row")
    p.add_argument("--quiet", action="store_true", help="Suppress console summary")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Set rate limit before Polygon client module initializes its token bucket.
    if not args.dry_run:
        os.environ.setdefault("POLYGON_REQUESTS_PER_SECOND", str(args.rate_limit))

    from scripts.verify.runner import print_console_summary, run_verification  # noqa: E402

    input_path = args.input
    if not input_path.exists():
        print(f"Error: input not found: {input_path}", file=sys.stderr)
        return 1

    fields = _parse_fields(args.fields)
    try:
        report = run_verification(
            input_path,
            dry_run=args.dry_run,
            sample=args.sample,
            seed=args.seed,
            tolerance_abs=args.tolerance,
            tolerance_rel=args.tolerance_rel,
            fields=fields,
            fail_fast=args.fail_fast,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path = args.output or _default_output_path(input_path.resolve())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    if not args.quiet:
        print_console_summary(report)
        print(f"Report written → {out_path}")

    if args.dry_run:
        return 0
    if report.summary.get("rows_fail", 0) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
