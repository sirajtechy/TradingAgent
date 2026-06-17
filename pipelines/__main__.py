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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


_load_env()

from pipelines.analyze import analyze_single, analyze_watchlist
from pipelines.backtest import run_sector_pilot, run_unified_pilot
from pipelines.daily import run_daily


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("analyze", help="Single-ticker or BUY/WATCH watchlist analyze (JSON)")
    pa.add_argument("--ticker", default=None, help="Required unless --watchlist")
    pa.add_argument("--watchlist", action="store_true", help="Analyze all BUY/WATCH from master_pilot")
    pa.add_argument(
        "--trade-focus",
        action="store_true",
        help="Watchlist: BUY + WATCH with Phoenix score > 60 only",
    )
    pa.add_argument("--max-tickers", type=int, default=None, help="Cap watchlist batch size")
    pa.add_argument(
        "--force",
        action="store_true",
        help="Re-analyze even when cached JSON exists (watchlist)",
    )
    pa.add_argument("--date", required=True, metavar="YYYY-MM-DD")
    pa.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "phoenix", "fundamental", "full"],
    )
    pa.add_argument("--fund-data-source", default="yfinance", choices=["yfinance", "fmp"])
    pa.add_argument(
        "--export-breakdown",
        action="store_true",
        help="Write agent_breakdown markdown (full fusion only; default path under data/output/research/)",
    )
    pa.add_argument(
        "--markdown-out",
        default=None,
        metavar="PATH",
        help="Override markdown output path (implies --export-breakdown)",
    )
    pa.add_argument(
        "--json-out",
        default=None,
        metavar="PATH",
        help="Write analyze JSON to PATH (default auto-save for full fusion or --export-breakdown)",
    )
    pa.add_argument(
        "--refresh-context",
        action="store_true",
        help="Re-run macro, market_summary, geopolitics cache (full fusion)",
    )
    pa.add_argument(
        "--strategy-profile",
        default="none",
        choices=["none", "minervini", "moglen", "breitstein", "mcintosh", "blend", "all"],
        help="Attach trader strategy intelligence layers",
    )

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
        import json

        if args.watchlist:
            doc = analyze_watchlist(
                as_of_date=args.date,
                fusion=args.fusion,
                fund_data_source=args.fund_data_source,
                export_breakdown=args.export_breakdown or bool(args.markdown_out),
                refresh_context=args.refresh_context,
                strategy_profile=args.strategy_profile,
                trade_focus_only=args.trade_focus,
                skip_cached=not args.force,
                max_tickers=args.max_tickers,
            )
            print(json.dumps(doc, indent=2, default=str))
            return 0 if doc.get("ok", True) else 1

        if not args.ticker:
            print("error: --ticker required unless --watchlist", file=sys.stderr)
            return 1

        export_breakdown = args.export_breakdown or bool(args.markdown_out)
        doc = analyze_single(
            ticker=args.ticker,
            as_of_date=args.date,
            fusion=args.fusion,
            fund_data_source=args.fund_data_source,
            export_breakdown=export_breakdown,
            markdown_out=args.markdown_out,
            json_out=args.json_out,
            refresh_context=args.refresh_context,
            strategy_profile=args.strategy_profile,
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
