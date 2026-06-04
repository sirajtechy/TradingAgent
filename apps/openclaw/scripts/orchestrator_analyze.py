#!/usr/bin/env python3
"""
Standalone wrapper for OpenClaw exec — delegates to ``pipelines.analyze`` (no duplicated fusion).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.analyze import analyze_single_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True, help="US ticker symbol")
    ap.add_argument("--date", required=True, metavar="YYYY-MM-DD", help="As-of date (no lookahead)")
    ap.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "phoenix", "fundamental"],
        help="Orchestration path (default phoenix-fa)",
    )
    ap.add_argument(
        "--fund-data-source",
        default="yfinance",
        choices=["yfinance", "fmp"],
        help="Fundamental data provider",
    )
    args = ap.parse_args()

    text = analyze_single_json(
        ticker=args.ticker,
        as_of_date=args.date,
        fusion=args.fusion,
        fund_data_source=args.fund_data_source,
    )
    print(text)
    doc = json.loads(text)
    return 0 if doc.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
