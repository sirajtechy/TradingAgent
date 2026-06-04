#!/usr/bin/env python3
"""
run_live_predictions.py — Live Orchestrator (CWAF) prediction runner.

Runs technical + fundamental agents through the orchestrator for all 50 tickers
as of today's date, producing pattern recognition, signals, and ranked predictions.

Usage
─────
    python scripts/run_live_predictions.py
    python scripts/run_live_predictions.py --sector Technology
    python scripts/run_live_predictions.py --tickers AAPL,NVDA,TSLA
    python scripts/run_live_predictions.py --workers 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths
from backtests.common import SECTORS, ALL_TICKERS

# ─────────────────────────────────────────────────────────────────────────────
# Worker
# ─────────────────────────────────────────────────────────────────────────────

def _analyze_ticker(ticker: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Run the full orchestrator pipeline for a single ticker (current date)."""
    from agents.orchestrator.service import analyze_ticker
    try:
        result = analyze_ticker(ticker=ticker, as_of_date=None)
        sig = result.get("final_signal", "?")
        score = result.get("orchestrator_score", 0)
        conf = result.get("final_confidence", 0)
        conflict = "⚡" if result.get("conflict_detected") else "✓"
        print(f"  {conflict} {ticker:<6} → {sig:<8}  score={score:.1f}  conf={conf:.2f}", flush=True)
        return ticker, result
    except Exception as exc:
        print(f"  ✗ {ticker:<6} → ERROR: {exc}", flush=True)
        return ticker, {"error": str(exc), "ticker": ticker}


def _get_tech_patterns(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract pattern detections from technical agent output."""
    tech = result.get("tech_output") or {}
    subscores = tech.get("subscores", {})
    return subscores.get("patterns", [])


def _get_sector(ticker: str) -> str:
    """Reverse-lookup sector for a ticker."""
    for sector, tickers in SECTORS.items():
        if ticker in tickers:
            return sector
    return "Unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────────────────────────────────────────

def build_prediction_report(results: Dict[str, Dict[str, Any]]) -> str:
    """Build a comprehensive markdown report from orchestrator results."""
    today = date.today().isoformat()
    lines = [
        f"# 🔮 Live Stock Predictions — {today}",
        f"**Agents**: Technical v2 (9 frameworks) + Fundamental v3 (6 evaluators) → Orchestrator CWAF Fusion",
        f"**Universe**: {len(results)} tickers across 5 sectors",
        "",
    ]

    # Categorize
    bullish, bearish, neutral, errors = [], [], [], []
    for ticker, r in sorted(results.items()):
        if "error" in r and "final_signal" not in r:
            errors.append((ticker, r))
            continue
        sig = r.get("final_signal", "neutral")
        entry = {
            "ticker": ticker,
            "sector": _get_sector(ticker),
            "signal": sig,
            "score": r.get("orchestrator_score", 0),
            "confidence": r.get("final_confidence", 0),
            "conflict": r.get("conflict_detected", False),
            "resolution": r.get("conflict_resolution"),
            "weights": r.get("weights_applied", {}),
            "tech": r.get("tech_output"),
            "fund": r.get("fund_output"),
            "tech_error": r.get("tech_error"),
            "fund_error": r.get("fund_error"),
            "note": r.get("note"),
        }
        if sig == "bullish":
            bullish.append(entry)
        elif sig == "bearish":
            bearish.append(entry)
        else:
            neutral.append(entry)

    # Sort by score (highest first for bullish, lowest for bearish)
    bullish.sort(key=lambda x: x["score"], reverse=True)
    bearish.sort(key=lambda x: x["score"])
    neutral.sort(key=lambda x: x["score"], reverse=True)

    # ── KPI Summary ──────────────────────────────────────────────────
    total = len(bullish) + len(bearish) + len(neutral)
    avg_score = sum(e["score"] for e in bullish + bearish + neutral) / total if total else 0
    conflict_count = sum(1 for e in bullish + bearish + neutral if e["conflict"])
    agreement_pct = ((total - conflict_count) / total * 100) if total else 0

    lines += [
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Analyzed | {total} |",
        f"| 🟢 Bullish | {len(bullish)} |",
        f"| 🔴 Bearish | {len(bearish)} |",
        f"| ⚪ Neutral | {len(neutral)} |",
        f"| Avg Orchestrator Score | {avg_score:.1f} |",
        f"| Agent Agreement Rate | {agreement_pct:.0f}% |",
        f"| Conflicts Detected | {conflict_count} |",
        f"| Errors | {len(errors)} |",
        "",
    ]

    # ── Sector Breakdown ─────────────────────────────────────────────
    sector_signals: Dict[str, Dict[str, int]] = {}
    for e in bullish + bearish + neutral:
        s = e["sector"]
        if s not in sector_signals:
            sector_signals[s] = {"bullish": 0, "bearish": 0, "neutral": 0}
        sector_signals[s][e["signal"]] += 1

    lines += ["## Sector Breakdown", "", "| Sector | Bullish | Bearish | Neutral | Dominant |"]
    lines += ["|--------|---------|---------|---------|----------|"]
    for sector, counts in sorted(sector_signals.items()):
        dominant = max(counts, key=counts.get)
        icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}[dominant]
        lines.append(f"| {sector} | {counts['bullish']} | {counts['bearish']} | {counts['neutral']} | {icon} {dominant} |")
    lines.append("")

    # ── Top Bullish Predictions ──────────────────────────────────────
    if bullish:
        lines += [
            "## 🟢 Top Bullish Predictions (ranked by score)",
            "",
            "| # | Ticker | Sector | Score | Confidence | Tech Signal | Fund Signal | Conflict | Weights (T/F) |",
            "|---|--------|--------|-------|------------|-------------|-------------|----------|---------------|",
        ]
        for i, e in enumerate(bullish, 1):
            tech_sig = e["tech"]["signal"] if e["tech"] else "ERR"
            fund_sig = e["fund"]["signal"] if e["fund"] else "ERR"
            tech_score = f'{e["tech"]["score"]:.0f}' if e["tech"] else "-"
            fund_score = f'{e["fund"]["score"]:.0f}' if e["fund"] else "-"
            w = e["weights"]
            wt = f'{w.get("tech", 0):.0f}/{w.get("fund", 0):.0f}'
            conflict_icon = "⚡" if e["conflict"] else "✓"
            lines.append(
                f"| {i} | **{e['ticker']}** | {e['sector']} | {e['score']:.1f} | "
                f"{e['confidence']:.2f} | {tech_sig} ({tech_score}) | {fund_sig} ({fund_score}) | "
                f"{conflict_icon} | {wt} |"
            )
        lines.append("")

    # ── Bearish Predictions ──────────────────────────────────────────
    if bearish:
        lines += [
            "## 🔴 Bearish Predictions (ranked by score, lowest first)",
            "",
            "| # | Ticker | Sector | Score | Confidence | Tech Signal | Fund Signal | Conflict | Resolution |",
            "|---|--------|--------|-------|------------|-------------|-------------|----------|------------|",
        ]
        for i, e in enumerate(bearish, 1):
            tech_sig = e["tech"]["signal"] if e["tech"] else "ERR"
            fund_sig = e["fund"]["signal"] if e["fund"] else "ERR"
            tech_score = f'{e["tech"]["score"]:.0f}' if e["tech"] else "-"
            fund_score = f'{e["fund"]["score"]:.0f}' if e["fund"] else "-"
            conflict_icon = "⚡" if e["conflict"] else "✓"
            res = e["resolution"] or "-"
            lines.append(
                f"| {i} | **{e['ticker']}** | {e['sector']} | {e['score']:.1f} | "
                f"{e['confidence']:.2f} | {tech_sig} ({tech_score}) | {fund_sig} ({fund_score}) | "
                f"{conflict_icon} | {res} |"
            )
        lines.append("")

    # ── Neutral / Abstain ────────────────────────────────────────────
    if neutral:
        lines += [
            "## ⚪ Neutral / Abstained (no directional signal)",
            "",
            "| Ticker | Sector | Score | Tech Signal | Fund Signal | Note |",
            "|--------|--------|-------|-------------|-------------|------|",
        ]
        for e in neutral:
            tech_sig = e["tech"]["signal"] if e["tech"] else "ERR"
            fund_sig = e["fund"]["signal"] if e["fund"] else "ERR"
            note = e.get("note") or e.get("resolution") or "-"
            lines.append(
                f"| {e['ticker']} | {e['sector']} | {e['score']:.1f} | {tech_sig} | {fund_sig} | {note} |"
            )
        lines.append("")

    # ── Conflict Analysis ────────────────────────────────────────────
    conflicts = [e for e in bullish + bearish + neutral if e["conflict"]]
    if conflicts:
        lines += [
            "## ⚡ Conflict Analysis (Tech vs Fundamental disagreements)",
            "",
            "| Ticker | Tech → | Fund → | Orchestrator → | Resolution | Winner Weight |",
            "|--------|--------|--------|----------------|------------|---------------|",
        ]
        for e in conflicts:
            tech_sig = e["tech"]["signal"] if e["tech"] else "?"
            fund_sig = e["fund"]["signal"] if e["fund"] else "?"
            res = e["resolution"] or "-"
            w = e["weights"]
            lines.append(
                f"| {e['ticker']} | {tech_sig} | {fund_sig} | **{e['signal']}** | {res} | T={w.get('tech',0):.0f}% F={w.get('fund',0):.0f}% |"
            )
        lines.append("")

    # ── High-Confidence Setups ───────────────────────────────────────
    high_conf = [e for e in bullish + bearish if e["confidence"] >= 0.60 and not e["conflict"]]
    if high_conf:
        high_conf.sort(key=lambda x: x["confidence"], reverse=True)
        lines += [
            "## ⭐ High-Confidence Setups (conf ≥ 0.60, no conflict)",
            "",
            "| Ticker | Signal | Score | Confidence | Sector |",
            "|--------|--------|-------|------------|--------|",
        ]
        for e in high_conf:
            icon = "🟢" if e["signal"] == "bullish" else "🔴"
            lines.append(
                f"| **{e['ticker']}** | {icon} {e['signal']} | {e['score']:.1f} | {e['confidence']:.2f} | {e['sector']} |"
            )
        lines.append("")

    # ── Detailed Per-Ticker Breakdown ────────────────────────────────
    lines += [
        "## 📋 Detailed Per-Ticker Breakdown",
        "",
    ]
    for e in bullish + bearish + neutral:
        icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}[e["signal"]]
        lines.append(f"### {icon} {e['ticker']} ({e['sector']})")
        lines.append("")
        lines.append(f"- **Orchestrator**: {e['signal']} | Score: {e['score']:.1f} | Confidence: {e['confidence']:.2f}")

        if e["tech"]:
            t = e["tech"]
            lines.append(f"- **Technical Agent**: {t['signal']} | Score: {t['score']:.1f} | Band: {t['band']} | ADX Conf: {t.get('adx_confidence', '-')}")
            if t.get("subscores"):
                subs = t["subscores"]
                sub_strs = []
                for k, v in sorted(subs.items()):
                    if isinstance(v, (int, float)):
                        sub_strs.append(f"{k}={v:.0f}")
                if sub_strs:
                    lines.append(f"  - Subscores: {', '.join(sub_strs)}")

        if e["fund"]:
            f_ = e["fund"]
            lines.append(f"- **Fundamental Agent**: {f_['signal']} | Score: {f_['score']:.1f} | Band: {f_['band']} | Data Quality: {f_.get('data_quality', '-')}")
            if f_.get("subscores"):
                subs = f_["subscores"]
                sub_strs = []
                for k, v in sorted(subs.items()):
                    if isinstance(v, (int, float)):
                        sub_strs.append(f"{k}={v:.0f}")
                if sub_strs:
                    lines.append(f"  - Subscores: {', '.join(sub_strs)}")

        if e["conflict"]:
            lines.append(f"- **Conflict**: {e['resolution']}")

        if e.get("note"):
            lines.append(f"- **Note**: {e['note']}")

        lines.append("")

    # ── Errors ───────────────────────────────────────────────────────
    if errors:
        lines += ["## ❌ Errors", ""]
        for ticker, r in errors:
            lines.append(f"- **{ticker}**: {r.get('error', 'Unknown error')}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Live orchestrator predictions")
    parser.add_argument("--sector", default=None, help="Run a single sector")
    parser.add_argument("--tickers", default=None, help="Comma-separated ticker list")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    parser.add_argument("--output-dir", default=str(paths.PREDICTIONS_DIR), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif args.sector:
        tickers = SECTORS[args.sector]
    else:
        tickers = ALL_TICKERS

    today = date.today().isoformat()
    print(f"\n{'='*70}")
    print(f"  LIVE PREDICTIONS — {today}")
    print(f"  Orchestrator CWAF (Technical v2 + Fundamental v3)")
    print(f"  {len(tickers)} tickers | {args.workers} workers")
    print(f"{'='*70}\n")

    results: Dict[str, Any] = {}
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        fut_map = {pool.submit(_analyze_ticker, t): t for t in tickers}
        for fut in as_completed(fut_map):
            ticker, result = fut.result()
            results[ticker] = result

            # Save per-ticker JSON as we go
            if result:
                (output_dir / f"{ticker}_prediction_{today}.json").write_text(
                    json.dumps(result, indent=2, default=str)
                )

    elapsed = time.time() - t0

    # Save consolidated results
    consolidated_path = output_dir / f"predictions_{today}.json"
    consolidated_path.write_text(json.dumps(results, indent=2, default=str))

    # Build and save the report
    report = build_prediction_report(results)
    report_path = output_dir / f"predictions_{today}.md"
    report_path.write_text(report)

    # Print summary to terminal
    print(f"\n{'='*70}")
    print(f"  COMPLETE — {len(results)} tickers in {elapsed:.0f}s")
    print(f"{'='*70}")

    # Quick signal counts
    signals = {"bullish": 0, "bearish": 0, "neutral": 0, "error": 0}
    for r in results.values():
        if "error" in r and "final_signal" not in r:
            signals["error"] += 1
        else:
            signals[r.get("final_signal", "neutral")] += 1

    print(f"\n  🟢 Bullish: {signals['bullish']}")
    print(f"  🔴 Bearish: {signals['bearish']}")
    print(f"  ⚪ Neutral: {signals['neutral']}")
    if signals['error']:
        print(f"  ❌ Errors:  {signals['error']}")

    print(f"\n  📄 Report: {report_path}")
    print(f"  📦 Data:   {consolidated_path}")
    print()


if __name__ == "__main__":
    main()
