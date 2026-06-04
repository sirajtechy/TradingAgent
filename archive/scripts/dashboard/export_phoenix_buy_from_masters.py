#!/usr/bin/env python3
"""
Legacy entry — delegates to ``core.io.export`` (BUY-only sheet preserved via All_Signals + BUY).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.io.export import DEFAULT_XLSX, export_signals  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-date", required=True, metavar="YYYY-MM-DD")
    ap.add_argument("--to-date", required=True, metavar="YYYY-MM-DD")
    ap.add_argument("--output", type=Path, default=DEFAULT_XLSX)
    ap.add_argument(
        "--signals",
        default="BUY",
        help="Comma-separated Phoenix signals (default BUY for backward compatibility)",
    )
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()
    d0 = date.fromisoformat(args.from_date)
    d1 = date.fromisoformat(args.to_date)
    sigs = [s.strip() for s in args.signals.split(",") if s.strip()]
    result = export_signals(
        date_from=d0,
        date_to=d1,
        signals=sigs,
        include_archive=not args.no_archive,
        output_xlsx=args.output,
        output_json=DEFAULT_XLSX.with_suffix(".json"),
    )
    s = result.summary
    print(f"Sources scanned: {s.get('sources_scanned')}")
    print(f"Signals (deduped): {s.get('signals_deduped')} (BUY={s.get('buy')}, WATCH={s.get('watch')})")
    out = args.output if args.output.is_absolute() else ROOT / args.output
    print(f"Wrote → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
