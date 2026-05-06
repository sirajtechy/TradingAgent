#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _validate_date_iso(d: str) -> str:
    datetime.strptime(d, "%Y-%m-%d")
    return d


def _parse_sectors(raw: str) -> List[str]:
    parts = [p.strip() for p in raw.split(",")]
    sectors = [p for p in parts if p]
    if not sectors:
        raise ValueError('No sectors provided. Example: --sectors "Energy,Industrials"')
    return sectors


def _load_sector_tickers(json_path: Path) -> Dict[str, List[str]]:
    data = json.loads(json_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {json_path}")
    out: Dict[str, List[str]] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, list):
            out[k] = [str(x).strip().upper() for x in v if str(x).strip()]
    return out


def _safe_sector_dirname(sector: str) -> str:
    return (
        sector.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("&", "and")
    )


@dataclass(frozen=True)
class _Job:
    ticker: str
    sector: str


def _run_one(job: _Job, as_of_date: str) -> Tuple[_Job, Dict[str, Any]]:
    """
    Worker entrypoint. Thread-based parallelism avoids macOS sandbox/semaphore
    limitations and is a good fit for IO-bound API calls.
    """
    from agents.phoenix.service import analyze_ticker

    result = analyze_ticker(ticker=job.ticker, as_of_date=as_of_date)
    result["sector"] = job.sector
    return job, result


def _summarize_one(d: Dict[str, Any]) -> Dict[str, Any]:
    stage = d.get("stage") or {}
    pattern = d.get("pattern") or {}
    entry = d.get("entry") or {}
    risk = d.get("risk") or {}

    return {
        "ticker": d.get("ticker"),
        "sector": d.get("sector"),
        "as_of_date": d.get("as_of_date"),
        "signal": d.get("signal"),
        "score": d.get("score"),
        "hard_filter_passed": d.get("hard_filter_passed"),
        "hard_filter_reason": d.get("hard_filter_reason"),
        "stage": {
            "stage": stage.get("stage"),
            "label": stage.get("label"),
            "action": stage.get("action"),
        } if stage else None,
        "pattern": {
            "pattern_name": pattern.get("pattern_name"),
            "confirmed": pattern.get("confirmed"),
            "volume_confirmed": pattern.get("volume_confirmed"),
            "pivot_price": pattern.get("pivot_price"),
            "confidence": pattern.get("confidence"),
        } if pattern else None,
        "entry": {
            "entry_type": entry.get("entry_type"),
            "entry_price": entry.get("entry_price"),
            "trigger_description": entry.get("trigger_description"),
        } if entry else None,
        "risk": {
            "stop_price": risk.get("stop_price"),
            "stop_pct": risk.get("stop_pct"),
            "target_1": risk.get("target_1"),
            "target_2": risk.get("target_2"),
            "reward_risk": risk.get("reward_risk"),
            "position_size_shares": risk.get("position_size_shares"),
            "trail_stop_ma": risk.get("trail_stop_ma"),
        } if risk else None,
        "warnings": d.get("warnings") or [],
        "report": d.get("report") or "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Phoenix Agent across ALL tickers for one or more sectors from "
            "data/halal_universe/halal_sector_tickers.json. Parallel via threads."
        )
    )
    parser.add_argument(
        "--sectors",
        required=True,
        help='Comma-separated sector keys from the JSON, e.g. "Information Technology,Industrials,Energy"',
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Cutoff date (YYYY-MM-DD). No future data is used.",
    )
    parser.add_argument(
        "--universe-json",
        default="data/halal_universe/halal_sector_tickers.json",
        help="Path to sector->tickers JSON.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, (os.cpu_count() or 4))),
        help="Number of parallel workers (threads).",
    )
    parser.add_argument(
        "--polygon-only",
        action="store_true",
        help="Disable yfinance fallback; use Polygon OHLCV only (recommended).",
    )
    parser.add_argument(
        "--output-dir",
        default="data/output/phoenix_sector_scans",
        help="Directory to write per-ticker JSON and consolidated summary.",
    )
    args = parser.parse_args()

    as_of_date = _validate_date_iso(args.date)
    requested_sectors = _parse_sectors(args.sectors)

    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    if args.polygon_only:
        os.environ["PHOENIX_POLYGON_ONLY"] = "1"

    universe_path = repo_root / args.universe_json
    sectors_map = _load_sector_tickers(universe_path)

    missing = [s for s in requested_sectors if s not in sectors_map]
    if missing:
        valid = ", ".join(sorted(sectors_map.keys()))
        raise SystemExit(f"Unknown sector(s): {missing}. Valid keys: {valid}")

    jobs: List[_Job] = []
    seen: set[str] = set()
    for sector in requested_sectors:
        for t in sectors_map.get(sector, []):
            if t not in seen:
                seen.add(t)
                jobs.append(_Job(ticker=t, sector=sector))

    out_root = repo_root / args.output_dir / as_of_date
    out_root.mkdir(parents=True, exist_ok=True)

    print(
        f"\nPHOENIX SECTOR SCAN — as_of={as_of_date}  sectors={len(requested_sectors)}  "
        f"tickers={len(jobs)}  workers={args.workers}"
    )
    print("──────────────────────────────────────────────────────────────────────────────")

    t0 = time.time()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(_run_one, job, as_of_date): job for job in jobs}
        for fut in as_completed(futs):
            job = futs[fut]
            try:
                _job, raw = fut.result()
                summary = _summarize_one(raw)
                results.append(summary)

                # Write per-ticker JSON to a sector folder for easy browsing.
                sector_dir = out_root / _safe_sector_dirname(job.sector)
                sector_dir.mkdir(parents=True, exist_ok=True)
                (sector_dir / f"{job.ticker}.json").write_text(json.dumps(summary, indent=2, default=str))

                sig = str(summary.get("signal") or "N/A")
                score = summary.get("score")
                score_s = f"{score:.1f}" if isinstance(score, (int, float)) else "N/A"
                filt = "PASS" if summary.get("hard_filter_passed") else "FAIL"
                print(f"✓ {job.ticker:<6}  {sig:<5}  score={score_s:>5}  filter={filt}  sector={job.sector}", flush=True)
            except Exception as exc:
                errors.append({"ticker": job.ticker, "sector": job.sector, "error": str(exc)})
                print(f"✗ {job.ticker:<6}  ERROR: {exc}", flush=True)

    elapsed = time.time() - t0

    # Deterministic ordering for downstream dashboard
    results.sort(key=lambda x: (str(x.get("sector") or ""), str(x.get("ticker") or "")))

    consolidated = {
        "meta": {
            "as_of_date": as_of_date,
            "sectors": requested_sectors,
            "tickers_requested": len(jobs),
            "results": len(results),
            "errors": len(errors),
            "workers": args.workers,
            "elapsed_sec": round(elapsed, 2),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "results": results,
        "errors": errors,
    }

    consolidated_path = out_root / f"phoenix_sector_scan_{as_of_date}.json"
    consolidated_path.write_text(json.dumps(consolidated, indent=2, default=str))

    print("\nDone.")
    print("Per-ticker JSON:", str(out_root))
    print("Consolidated   :", str(consolidated_path))
    print("")


if __name__ == "__main__":
    main()

