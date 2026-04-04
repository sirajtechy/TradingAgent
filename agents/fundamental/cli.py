import argparse
import json
import sys
from typing import Any

from .exceptions import FundamentalAgentError
from .service import analyze_ticker


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic fundamental analysis agent")
    parser.add_argument("ticker", help="Ticker symbol, for example AAPL")
    parser.add_argument("--as-of-date", help="Historical analysis date in YYYY-MM-DD format")
    parser.add_argument(
        "--shariah-standard",
        default="aaoifi",
        choices=["aaoifi", "djim", "sc_malaysia"],
        help="Shariah standard preset",
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json"],
        help="Output format",
    )
    parser.add_argument(
        "--no-experimental-score",
        action="store_true",
        help="Disable the experimental composite score",
    )
    parser.add_argument(
        "--data-source",
        default="fmp",
        choices=["fmp", "yfinance"],
        help="Data provider: fmp (default) or yfinance (free, any ticker)",
    )
    return parser


def main(argv: Any = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = analyze_ticker(
            ticker=args.ticker,
            as_of_date=args.as_of_date,
            shariah_standard=args.shariah_standard,
            include_experimental_score=not args.no_experimental_score,
            data_source=args.data_source,
        )
    except FundamentalAgentError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(result, indent=2, default=_json_default))
    else:
        print(result["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())