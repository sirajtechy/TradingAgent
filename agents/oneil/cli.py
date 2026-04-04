"""
cli.py — Command-line interface for the O'Neil CAN SLIM Technical Analysis Agent.

Usage
─────
    oneil-agent AAPL
    oneil-agent RELIANCE --exchange NSE --format json
    oneil-agent NVDA --as-of-date 2025-06-01
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="oneil-agent",
        description="O'Neil CAN SLIM Technical Analysis Agent — weekly chart pattern recognition + stage analysis",
    )
    p.add_argument("ticker", help="Stock ticker (e.g. AAPL, NVDA, RELIANCE)")
    p.add_argument(
        "--exchange",
        default="US",
        choices=["US", "NSE"],
        help="Exchange (default: US). Use NSE for Indian stocks.",
    )
    p.add_argument(
        "--as-of-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Analyse as-of this date (default: today). Useful for point-in-time analysis.",
    )
    p.add_argument(
        "--format",
        default="text",
        choices=["text", "json"],
        help="Output format (default: text).",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    as_of: date | None = None
    if args.as_of_date:
        try:
            as_of = date.fromisoformat(args.as_of_date)
        except ValueError:
            print(f"ERROR: --as-of-date must be YYYY-MM-DD, got: {args.as_of_date}", file=sys.stderr)
            sys.exit(1)

    # Lazy import — keeps startup fast when just running --help
    from .service import analyze_ticker
    from .data_client import DataError

    try:
        signal = analyze_ticker(
            ticker=args.ticker,
            as_of_date=as_of,
            exchange=args.exchange,
        )
    except DataError as exc:
        print(f"ERROR: Could not fetch data — {exc}", file=sys.stderr)
        sys.exit(2)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(signal.to_dict(), indent=2))
    else:
        _print_text(signal)


def _print_text(signal) -> None:
    from .models import ONeilSignal  # for type hints

    # Direction badge
    badge = {"BULLISH": "🟢 BULLISH", "BEARISH": "🔴 BEARISH", "NEUTRAL": "⚪ NEUTRAL"}.get(
        signal.direction, signal.direction
    )

    w = 60
    print("─" * w)
    print(f"  O'Neil CAN SLIM Analysis — {signal.ticker}  ({signal.as_of_date})")
    print("─" * w)
    print(f"  Direction : {badge}   (strength {signal.signal_strength:.2f})")
    print(f"  Stage     : {signal.market_stage} — {signal.stage_description}")
    print()

    if signal.pattern_detected:
        ps = f"  Pattern   : {signal.pattern_detected}"
        if signal.is_late_stage:
            ps += "  ⚠️  LATE STAGE"
        if signal.volume_dry_up:
            ps += "  📉 Vol Dry-Up"
        print(ps)
    else:
        print("  Pattern   : None detected")

    print()
    print("  ── Indicators (Weekly) ──────────────────────────────")
    _ind = lambda v, n=2: f"{v:.{n}f}" if v is not None else "N/A"
    print(f"  RSI(14w)         : {_ind(signal.rsi_14w)}")
    print(f"  MACD histogram   : {_ind(signal.macd_histogram, 4)}")
    print(f"  EMA(10w)         : {_ind(signal.ema_10w)}")
    print(f"  EMA(21w)         : {_ind(signal.ema_21w)}")
    print(f"  EMA(50w)         : {_ind(signal.ema_50w)}")
    print(f"  SMA(30w)         : {_ind(signal.sma_30w)}")
    print(f"  EMA(200d)        : {_ind(signal.ema_200d)}")
    print(f"  Vol ratio(10w)   : {_ind(signal.volume_ratio_10w)}×")
    print()
    print(f"  Confluence       : {signal.confluence_score}/4  {signal.confluence_detail}")
    print()

    if signal.entry_price:
        rr = f"{signal.risk_reward_ratio:.1f}:1" if signal.risk_reward_ratio else "N/A"
        print("  ── Trade Levels ─────────────────────────────────────")
        print(f"  Last Close  : ${signal.last_close:.2f}")
        print(f"  Entry       : ${signal.entry_price:.2f}   (pivot / breakout level)")
        print(f"  Stop Loss   : ${signal.stop_loss:.2f}   (−7% from entry)")
        print(f"  Target      : ${signal.target_price:.2f}   (measured move)")
        print(f"  R/R         : {rr}")
        print()

    if signal.warnings:
        print("  ── Warnings ─────────────────────────────────────────")
        for w in signal.warnings:
            print(f"  ⚠  {w}")
        print()

    print("─" * w)


if __name__ == "__main__":
    main()
