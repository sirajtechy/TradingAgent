"""
cli.py — Command-line interface for the technical analysis agent.

Usage:
    python -m technical_agent AAPL
    python -m technical_agent AAPL --as-of-date 2025-10-01
    python -m technical_agent AAPL --as-of-date 2025-10-01 --format json
"""

import argparse
import json
import sys
from typing import Any

from .exceptions import TechnicalAgentError
from .service import analyze_ticker


def _json_default(value: Any) -> Any:
    """Handle date serialisation and strip internal objects."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # PatternSignal objects embedded in dicts — skip them
    if hasattr(value, "__dataclass_fields__"):
        return str(value)
    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the technical agent CLI."""
    parser = argparse.ArgumentParser(
        description="Deterministic technical analysis agent — 7 frameworks "
                    "with chart pattern recognition"
    )
    parser.add_argument(
        "ticker",
        help="Ticker symbol, e.g. AAPL",
    )
    parser.add_argument(
        "--as-of-date",
        help="Historical analysis date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json"],
        help="Output format (default: text)",
    )
    return parser


def main(argv: Any = None) -> int:
    """
    Entry-point for ``python -m technical_agent``.

    Returns:
        Exit code: 0 on success, 1 on handled error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = analyze_ticker(
            ticker=args.ticker,
            as_of_date=args.as_of_date,
        )
    except TechnicalAgentError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        # Strip internal _signal_obj keys before serialisation
        _strip_internal_keys(result)
        print(json.dumps(result, indent=2, default=_json_default))
    else:
        print(result.get("report", "(no report generated)"))

    return 0


def _strip_internal_keys(obj: Any) -> None:
    """Recursively remove keys starting with ``_`` from dicts."""
    if isinstance(obj, dict):
        keys_to_remove = [k for k in obj if isinstance(k, str) and k.startswith("_")]
        for k in keys_to_remove:
            del obj[k]
        for v in obj.values():
            _strip_internal_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            _strip_internal_keys(item)


if __name__ == "__main__":
    raise SystemExit(main())
