#!/usr/bin/env python3
"""
run_halal_predictions.py — Batch predict_trade() runner for the full Halal universe.

Reads data/halal_universe/halal_sector_tickers.json and runs the complete
TA + FA orchestrator pipeline for every ticker as of today's date.

Usage
─────
    python scripts/run_halal_predictions.py
    python scripts/run_halal_predictions.py --workers 6
    python scripts/run_halal_predictions.py --date 2026-04-04
    python scripts/run_halal_predictions.py --sector "Information Technology"

Output
──────
    data/output/predictions/halal_<date>/         ← one JSON per ticker
    data/output/predictions/halal_<date>_summary.json
    data/output/predictions/halal_<date>_summary.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HALAL_UNIVERSE = Path(__file__).parent.parent / "data" / "halal_universe" / "halal_sector_tickers.json"
OUTPUT_BASE    = Path(__file__).parent.parent / "data" / "output" / "predictions"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_trading_day(d: date) -> date:
    """Return d if weekday, else step back to Friday."""
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _load_tickers(sector_filter: Optional[str] = None) -> Dict[str, List[str]]:
    """Load and deduplicate tickers from halal universe JSON."""
    raw: Dict[str, List[str]] = json.loads(HALAL_UNIVERSE.read_text())
    seen = set()
    result: Dict[str, List[str]] = {}
    for sector, tickers in raw.items():
        if sector_filter and sector.lower() != sector_filter.lower():
            continue
        clean = []
        for t in tickers:
            if " " in t or len(t) > 6:
                continue   # skip WI tickers and malformed symbols
            if t not in seen:
                seen.add(t)
                clean.append(t)
        if clean:
            result[sector] = clean
    return result


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _predict_ticker(
    ticker: str,
    sector: str,
    cutoff_str: str,
    target_days: int,
) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """
    Run predict_trade() for a single ticker.
    Returns (ticker, sector, result_dict | None).
    """
    from agents.technical.service import predict_trade
    try:
        result = predict_trade(ticker=ticker, cutoff_date=cutoff_str, target_days=target_days)
        result["sector"] = sector
        trade    = result.get("trade")
        outcome  = trade["exit_outcome"] if trade else "NO_TRADE"
        source   = trade["entry_source"][:40] if trade else (result.get("no_trade_reason") or "")[:40]
        signal   = result.get("sentiment", "?")
        score    = result.get("confidence_score", 0)
        print(f"  {'✓' if trade else '·'} {ticker:<6} [{signal:<8}] score={score:.0f}  {outcome:<12} {source}", flush=True)
        return ticker, sector, result
    except Exception as exc:
        msg = str(exc)
        print(f"  ✗ {ticker:<6} ERROR: {msg[:70]}", flush=True)
        return ticker, sector, {"ticker": ticker, "sector": sector, "error": msg}


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def _build_summary(
    results: List[Dict[str, Any]],
    cutoff_date: str,
    target_days: int,
    elapsed: float,
) -> Dict[str, Any]:
    trades, no_trades, errors = [], [], []

    for r in results:
        if "error" in r and "sentiment" not in r:
            errors.append(r)
            continue
        trade = r.get("trade")
        entry = {
            "ticker":           r.get("ticker", "?"),
            "sector":           r.get("sector", "Unknown"),
            "sentiment":        r.get("sentiment", "?"),
            "confidence_score": r.get("confidence_score", 0),
            "tech_score":       r.get("tech_score", 0),
            "fund_score":       r.get("fund_score", 0),
            "conflict":         r.get("conflict_detected", False),
            "no_trade_reason":  r.get("no_trade_reason"),
        }
        if trade:
            entry.update({
                "entry_date":       trade["entry_date"],
                "entry_price":      trade["entry_price"],
                "entry_source":     trade["entry_source"],
                "exit_date":        trade["exit_date"],
                "exit_price":       trade["exit_price"],
                "exit_outcome":     trade["exit_outcome"],
                "holding_days":     trade["holding_days"],
                "gross_profit_pct": trade["gross_profit_pct"],
                "net_profit_pct":   trade["net_profit_pct"],
                "stop_loss":        trade["stop_loss"],
                "target_price":     trade["target_price"],
                "reward_risk_ratio":trade["reward_risk_ratio"],
            })
            trades.append(entry)
        else:
            entry["no_trade_reason"] = r.get("no_trade_reason", "")
            no_trades.append(entry)

    trades.sort(key=lambda x: x.get("gross_profit_pct", 0), reverse=True)

    return {
        "run_meta": {
            "cutoff_date": cutoff_date,
            "target_days": target_days,
            "run_date":    datetime.now().isoformat(),
            "elapsed_sec": round(elapsed, 1),
            "total":       len(results),
            "trades":      len(trades),
            "no_trades":   len(no_trades),
            "errors":      len(errors),
        },
        "trades":    trades,
        "no_trades": no_trades,
        "errors":    errors,
    }


def _build_markdown(summary: Dict[str, Any]) -> str:
    meta   = summary["run_meta"]
    trades = summary["trades"]
    no_tr  = summary["no_trades"]
    errs   = summary["errors"]

    lines = [
        f"# Halal Universe — Trade Predictions",
        f"",
        f"**Cutoff date**: {meta['cutoff_date']}  |  **Max window**: {meta['target_days']} trading days  |  "
        f"**Run**: {meta['run_date'][:16]}  |  **Elapsed**: {meta['elapsed_sec']}s",
        f"",
        f"## Summary",
        f"",
        f"| | Count |",
        f"|---|---|",
        f"| Total analyzed | {meta['total']} |",
        f"| **Active trades** (pattern-driven) | **{meta['trades']}** |",
        f"| No trade (stale / neutral / no pattern) | {meta['no_trades']} |",
        f"| Errors (data unavailable) | {meta['errors']} |",
        f"",
    ]

    # Sector breakdown of trades
    sector_trades: Dict[str, int] = {}
    sector_outcomes: Dict[str, Dict[str, int]] = {}
    for t in trades:
        s = t["sector"]
        sector_trades[s] = sector_trades.get(s, 0) + 1
        if s not in sector_outcomes:
            sector_outcomes[s] = {}
        o = t.get("exit_outcome", "?")
        sector_outcomes[s][o] = sector_outcomes[s].get(o, 0) + 1

    if sector_trades:
        lines += [
            "## Trades by Sector",
            "",
            "| Sector | Trades | OPEN | HIT_TARGET | HIT_STOP | EXPIRED |",
            "|--------|--------|------|------------|----------|---------|",
        ]
        for s in sorted(sector_trades):
            oc = sector_outcomes.get(s, {})
            lines.append(
                f"| {s} | {sector_trades[s]} | "
                f"{oc.get('OPEN',0)} | {oc.get('HIT_TARGET',0)} | {oc.get('HIT_STOP',0)} | {oc.get('EXPIRED',0)} |"
            )
        lines.append("")

    # Active trade table
    if trades:
        hit_t = [t for t in trades if t.get("exit_outcome") == "HIT_TARGET"]
        hit_s = [t for t in trades if t.get("exit_outcome") == "HIT_STOP"]
        exp   = [t for t in trades if t.get("exit_outcome") == "EXPIRED"]
        open_ = [t for t in trades if t.get("exit_outcome") == "OPEN"]

        def _trade_section(title, items):
            if not items:
                return []
            hdr = [
                f"## {title}",
                "",
                "| Ticker | Sector | Entry Date | Entry $ | Exit Date | Exit $ | "
                "Gross % | Net % | Pattern | R/R | Stop | Target |",
                "|--------|--------|------------|---------|-----------|--------|"
                "---------|-------|---------|-----|------|--------|",
            ]
            rows = []
            for t in items:
                rows.append(
                    f"| **{t['ticker']}** | {t['sector']} | {t['entry_date']} | "
                    f"{t['entry_price']:.2f} | {t['exit_date']} | {t['exit_price']:.2f} | "
                    f"{t.get('gross_profit_pct',0):+.2f}% | {t.get('net_profit_pct',0):+.2f}% | "
                    f"{t.get('entry_source','').replace('pattern:','')} | "
                    f"{t.get('reward_risk_ratio') or '-'} | "
                    f"{t.get('stop_loss',0):.2f} | {t.get('target_price',0):.2f} |"
                )
            return hdr + rows + [""]

        lines += _trade_section("OPEN — Live Setups (enter Monday 2026-04-06)", open_)
        lines += _trade_section("HIT_TARGET — Winning Trades (simulated)", hit_t)
        lines += _trade_section("EXPIRED — Held Full Window", exp)
        lines += _trade_section("HIT_STOP — Stopped Out", hit_s)

    # Error summary (top 10)
    if errs:
        lines += [
            f"## Errors ({len(errs)} tickers — insufficient data)",
            "",
            "| Ticker | Sector | Reason |",
            "|--------|--------|--------|",
        ]
        for e in errs[:30]:
            msg = str(e.get("error", ""))[:80]
            lines.append(f"| {e.get('ticker','?')} | {e.get('sector','?')} | {msg} |")
        if len(errs) > 30:
            lines.append(f"| ... | ... | +{len(errs)-30} more errors omitted |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=5,
                        help="Parallel workers (default 5 — respects Polygon rate limits)")
    parser.add_argument("--date", type=str, default=None,
                        help="Cutoff date YYYY-MM-DD (default: last trading day)")
    parser.add_argument("--target-days", type=int, default=20)
    parser.add_argument("--sector", type=str, default=None,
                        help="Filter to one sector only")
    args = parser.parse_args()

    # Resolve cutoff
    if args.date:
        cutoff = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        cutoff = _last_trading_day(date.today())
    cutoff_str = cutoff.isoformat()

    # Load tickers
    sector_map = _load_tickers(args.sector)
    flat: List[Tuple[str, str]] = []
    for sector, tickers in sector_map.items():
        for t in tickers:
            flat.append((t, sector))

    total = len(flat)
    print(f"\nHalal Universe Batch Prediction")
    print(f"Cutoff: {cutoff_str}  |  Target days: {args.target_days}  |  Workers: {args.workers}")
    print(f"Tickers: {total} across {len(sector_map)} sectors")
    print("─" * 70)

    # Output directory
    tag = f"halal_{cutoff_str}"
    out_dir = OUTPUT_BASE / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_predict_ticker, ticker, sector, cutoff_str, args.target_days): (ticker, sector)
            for ticker, sector in flat
        }
        done = 0
        for future in as_completed(futures):
            ticker, sector, result = future.result()
            done += 1
            if result:
                result["ticker"] = ticker
                result["sector"] = sector
                results.append(result)
                # Save individual file
                (out_dir / f"{ticker}.json").write_text(
                    json.dumps(result, indent=2, default=str)
                )
            eta = (time.time() - start) / done * (total - done)
            print(f"  Progress: {done}/{total}  ETA: {eta:.0f}s", end="\r", flush=True)

    elapsed = time.time() - start
    print(f"\n\nDone in {elapsed:.0f}s  ({elapsed/len(results):.1f}s/ticker avg)")

    # Build and save summary
    summary = _build_summary(results, cutoff_str, args.target_days, elapsed)
    md      = _build_markdown(summary)

    summary_json = OUTPUT_BASE / f"{tag}_summary.json"
    summary_md   = OUTPUT_BASE / f"{tag}_summary.md"

    summary_json.write_text(json.dumps(summary, indent=2, default=str))
    summary_md.write_text(md)

    print(f"\nResults saved to:")
    print(f"  {out_dir}  ({len(results)} individual JSONs)")
    print(f"  {summary_json}")
    print(f"  {summary_md}")
    print(f"\n── Quick Stats ─────────────────────────────────────────")
    meta = summary["run_meta"]
    print(f"  Trades generated : {meta['trades']}")
    print(f"  No-trade         : {meta['no_trades']}")
    print(f"  Errors           : {meta['errors']}")

    trades = summary["trades"]
    if trades:
        hit_t = [t for t in trades if t.get("exit_outcome") == "HIT_TARGET"]
        hit_s = [t for t in trades if t.get("exit_outcome") == "HIT_STOP"]
        exp   = [t for t in trades if t.get("exit_outcome") == "EXPIRED"]
        open_ = [t for t in trades if t.get("exit_outcome") == "OPEN"]
        print(f"  OPEN (live)      : {len(open_)}")
        print(f"  HIT_TARGET       : {len(hit_t)}")
        print(f"  EXPIRED          : {len(exp)}")
        print(f"  HIT_STOP         : {len(hit_s)}")
        if exp:
            avg_pct = sum(t.get("net_profit_pct", 0) for t in exp) / len(exp)
            print(f"  Avg net % (expired): {avg_pct:+.2f}%")
        print("\nTop 10 by gross profit:")
        for t in trades[:10]:
            print(f"  {t['ticker']:<6} {t.get('exit_outcome','?'):<12} {t.get('gross_profit_pct',0):+6.2f}%  via {t.get('entry_source','')}")


if __name__ == "__main__":
    main()
