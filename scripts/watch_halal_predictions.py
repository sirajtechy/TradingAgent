#!/usr/bin/env python3
"""
watch_halal_predictions.py

Watches a prediction output folder and rebuilds the combined JSON
for the backtest dashboard whenever new ticker files appear.

Usage:
    python3 scripts/watch_halal_predictions.py \
        --input-dir  data/output/predictions/halal_2026-04-04 \
        --output     ../backtest-dashboard/app/data/halal-predictions.json \
        --interval   10
"""

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone


def load_all(input_dir: str) -> list[dict]:
    records = []
    for fpath in sorted(glob.glob(os.path.join(input_dir, "*.json"))):
        try:
            with open(fpath) as f:
                d = json.load(f)
            records.append(d)
        except Exception as e:
            print(f"  [warn] {os.path.basename(fpath)}: {e}", flush=True)
    return records


def normalize(raw: dict) -> dict:
    """Apply same defaults as the dashboard to handle incomplete records."""
    return {
        "ticker": raw.get("ticker", "???"),
        "sector": raw.get("sector", "Unknown"),
        "cutoff_date": raw.get("cutoff_date", ""),
        "target_days_requested": raw.get("target_days_requested", 0),
        "sentiment": raw.get("sentiment", "neutral"),
        "confidence_score": raw.get("confidence_score", 0),
        "confidence_pct": raw.get("confidence_pct", 0),
        "tech_score": raw.get("tech_score", 0),
        "fund_score": raw.get("fund_score", 0),
        "fusion_weights": raw.get("fusion_weights") or {"tech": 0, "fund": 0},
        "conflict_detected": raw.get("conflict_detected", False),
        "conflict_resolution": raw.get("conflict_resolution"),
        "patterns": raw.get("patterns") or [],
        "signal_alignment": raw.get("signal_alignment") or {
            "signal_count": 0,
            "bullish_frameworks": 0,
            "entry_rules_met": 0,
            "confidence_pct": 0,
            "confidence_label": "none",
        },
        "orchestrator_score": raw.get("orchestrator_score", 0),
        "orchestrator_confidence": raw.get("orchestrator_confidence", 0),
        "trade": raw.get("trade"),
        "no_trade_reason": raw.get("no_trade_reason"),
    }


def build_output(records: list[dict], input_dir: str) -> dict:
    normalized = [normalize(r) for r in records]

    # Derive meta from first valid record
    first = records[0] if records else {}
    cutoff = first.get("cutoff_date", "unknown")
    target_days = first.get("target_days_requested", 20)

    # Sentiment counts
    sentiments = {"bullish": 0, "bearish": 0, "neutral": 0}
    for p in normalized:
        s = p["sentiment"]
        if s in sentiments:
            sentiments[s] += 1

    return {
        "meta": {
            "date": cutoff,
            "totalTickers": len(normalized),
            "targetDays": target_days,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "inputDir": os.path.abspath(input_dir),
        },
        "summary": sentiments,
        "predictions": normalized,
    }


def write_atomic(path: str, data: dict) -> None:
    """Write to a tmp file then rename so the dashboard never reads a partial file."""
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description="Watch halal prediction folder and update dashboard JSON")
    parser.add_argument(
        "--input-dir",
        default="data/output/predictions/halal_2026-04-04",
        help="Folder containing per-ticker JSON files",
    )
    parser.add_argument(
        "--output",
        default="../backtest-dashboard/app/data/halal-predictions.json",
        help="Output path for combined dashboard JSON",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Poll interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no watch loop)",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output    = args.output

    if not os.path.isdir(input_dir):
        print(f"[error] input-dir not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[watch] Watching : {os.path.abspath(input_dir)}")
    print(f"[watch] Output   : {os.path.abspath(output)}")
    print(f"[watch] Interval : {args.interval}s")
    print(f"[watch] Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    last_count = -1
    last_mtime = 0.0

    while True:
        try:
            files = sorted(glob.glob(os.path.join(input_dir, "*.json")))
            current_count = len(files)

            # Detect any change: new file count OR newest file modified
            newest_mtime = max((os.path.getmtime(f) for f in files), default=0.0)
            changed = (current_count != last_count) or (newest_mtime > last_mtime)

            if changed:
                records = load_all(input_dir)
                output_data = build_output(records, input_dir)
                write_atomic(output, output_data)

                now = datetime.now().strftime("%H:%M:%S")
                delta = "" if last_count < 0 else f" (+{current_count - last_count})"
                print(
                    f"[{now}] Updated → {current_count} tickers{delta} | "
                    f"B={output_data['summary']['bullish']} "
                    f"Be={output_data['summary']['bearish']} "
                    f"N={output_data['summary']['neutral']} | "
                    f"→ {output}",
                    flush=True,
                )
                last_count = current_count
                last_mtime = newest_mtime
            else:
                # Print a dot every ~60s so you know it's alive
                pass

        except KeyboardInterrupt:
            print("\n[watch] Stopped.")
            break
        except Exception as e:
            print(f"[error] {e}", flush=True)

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
