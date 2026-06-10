#!/usr/bin/env python3
"""
python -m pipelines — agnostic workflow entry (delegates to existing engines).

Examples:
  python -m pipelines analyze --ticker AAPL --date 2026-05-20 --fusion phoenix-fa
  python -m pipelines sector --sector Energy --signal-date 2026-05-20
  python -m pipelines unified --signal-date 2026-05-20
  python -m pipelines daily --signal-date 2026-05-20
"""

from __future__ import annotations

import argparse
import sys

from pipelines.analyze import analyze_single
from pipelines.backtest import run_sector_pilot, run_unified_pilot
from pipelines.daily import run_daily


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("analyze", help="Single-ticker analyze (OpenClaw / JSON)")
    pa.add_argument("--ticker", required=True)
    pa.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    pa.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "phoenix", "fundamental", "full"],
    )
    pa.add_argument("--fund-data-source", default="yfinance", choices=["yfinance", "fmp"])

    ps = sub.add_parser("sector", help="Single-sector master pilot")
    ps.add_argument("--sector", required=True)
    ps.add_argument("--signal-date", required=True)
    ps.add_argument("--eval-days", type=int, default=15)

    pu = sub.add_parser("unified", help="All-sector unified master pilot")
    pu.add_argument("--signal-date", required=True)
    pu.add_argument("--eval-days", type=int, default=15)
    pu.add_argument("--sector-jobs", type=int, default=11)
    pu.add_argument("--workers", type=int, default=8)
    pu.add_argument("--period-workers", type=int, default=2)

    pd = sub.add_parser("daily", help="Daily pipeline (unified + BUY excel + notify)")
    pd.add_argument("--signal-date", default=None)
    pd.add_argument("--eval-days", type=int, default=15)
    pd.add_argument("--no-export-buy", action="store_true")
    pd.add_argument("--no-telegram", action="store_true")

    args = p.parse_args(argv)

    if args.command == "analyze":
        doc = analyze_single(
            ticker=args.ticker,
            as_of_date=args.date,
            fusion=args.fusion,
            fund_data_source=args.fund_data_source,
        )
        import json

        print(json.dumps(doc, indent=2, default=str))
        return 0 if doc.get("ok", True) else 1

    if args.command == "sector":
        return run_sector_pilot(
            sector=args.sector,
            signal_date=args.signal_date,
            eval_days=args.eval_days,
        )

    if args.command == "unified":
        return run_unified_pilot(
            signal_date=args.signal_date,
            eval_days=args.eval_days,
            sector_jobs=args.sector_jobs,
            workers=args.workers,
            period_workers=args.period_workers,
        )

    if args.command == "daily":
        return run_daily(
            signal_date=args.signal_date,
            export_buy=not args.no_export_buy,
            send_telegram=not args.no_telegram,
            eval_days=args.eval_days,
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
