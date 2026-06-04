#!/usr/bin/env python3
"""
run_halal_sector_month_pilot.py
================================
**Single canonical** Phoenix + Fundamental **labeled window backtest** (one signal date +
evaluation horizon). Universe is **agnostic** — choose exactly one of:

  • ``--tickers A`` or ``--tickers A,B,C`` — explicit symbol list (any US symbols;
    sector on each row comes from ``halal_sector_tickers.json`` when listed).
  • ``--sector "Information Technology"`` — halal sector from ``halal_sector_tickers.json``,
    combined with ``--limit`` and optional ``--random-sample``.

Outputs (same path for every run):

  - per-ticker JSON under output-dir/per_ticker/
  - pilot_manifest.json (no-lookahead statement)
  - pilot_results.json
  - confusion_matrix.json
  - run_bundle.json → ``backtest-dashboard`` → ``/trading-runs``

CLI wrapper: ``python scripts/run_trading.py backtest --engine halal-sector-pilot -- --tickers AMAT ...``

Do not duplicate this flow in new scripts — extend this file or ``run_trading.py`` only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import paths  # noqa: E402

HALAL_JSON = paths.HALAL_UNIVERSE / "halal_sector_tickers.json"


def _resolve_sector(sector_query: str) -> str:
    raw: Dict[str, List[str]] = json.loads(HALAL_JSON.read_text())
    q = sector_query.strip().lower()
    for k in raw.keys():
        if k.lower() == q:
            return k
    raise SystemExit(
        f'Unknown halal sector "{sector_query}". '
        f'Example keys: {", ".join(sorted(raw.keys())[:8])} …'
    )


def _sector_full_list(canon: str) -> List[str]:
    raw: Dict[str, List[str]] = json.loads(HALAL_JSON.read_text())
    return [str(t).strip().upper() for t in raw[canon] if str(t).strip()]


def load_sector_tickers(
    sector_query: str,
    limit: Optional[int],
    offset: int,
    seed: Optional[int],
    random_draw: bool,
) -> Tuple[str, List[str]]:
    canon = _resolve_sector(sector_query)
    all_clean = _sector_full_list(canon)
    if random_draw:
        import random

        if limit is None:
            raise SystemExit("--random-sample requires --limit")
        rng = random.Random(seed or 42)
        if limit > len(all_clean):
            raise SystemExit(f"--limit {limit} > sector size {len(all_clean)}")
        return canon, rng.sample(all_clean, limit)
    sliced = all_clean[int(offset) :]
    if limit is not None:
        sliced = sliced[: int(limit)]
    return canon, sliced


def _run_ticker(
    ticker: str,
    months: List[Tuple[date, date]],
    period_workers: int,
) -> Dict[str, Any]:
    from agents.orchestrator.backtest_phoenix import run_monthly_backtest

    return run_monthly_backtest(ticker=ticker, months=months, period_workers=period_workers)


def _confusion_target_hit(df: pd.DataFrame) -> Dict[str, Any]:
    """Same semantics as run_phoenix_fund_orchestrator_backtest_2025._confusion_from_periods."""
    TP = FP = TN = FN = neutral = errors = 0
    for _, r in df.iterrows():
        sig = r.get("signal")
        corr = r.get("signal_correct")
        if pd.isna(corr):
            neutral += 1
            continue
        corr = bool(corr)
        if sig not in ("bullish", "bearish"):
            neutral += 1
            continue
        if sig == "bullish" and corr is True:
            TP += 1
        elif sig == "bullish" and corr is False:
            FP += 1
        elif sig == "bearish" and corr is True:
            TN += 1
        elif sig == "bearish" and corr is False:
            FN += 1
        else:
            errors += 1

    directional = TP + FP + TN + FN
    correct = TP + TN

    def pct(v: Optional[float]) -> Optional[float]:
        return round(v * 100, 1) if v is not None else None

    acc = correct / directional if directional else None
    prec = TP / (TP + FP) if (TP + FP) else None
    rec = TP / (TP + FN) if (TP + FN) else None
    spec = TN / (TN + FP) if (TN + FP) else None
    f1 = (
        (2 * prec * rec / (prec + rec))
        if (prec is not None and rec is not None and (prec + rec) > 0)
        else None
    )
    abst = neutral / (neutral + directional) if (neutral + directional) else None

    return {
        "TP": TP,
        "FP": FP,
        "TN": TN,
        "FN": FN,
        "directional": directional,
        "correct": correct,
        "neutral": neutral,
        "errors": errors,
        "accuracy_pct": pct(acc),
        "precision_pct": pct(prec),
        "recall_pct": pct(rec),
        "specificity_pct": pct(spec),
        "f1_pct": pct(f1),
        "abstention_pct": pct(abst),
    }


def _pct_long(entry: Any, target: Any) -> Optional[float]:
    """Simple long P&L %: (target - entry) / entry * 100."""
    try:
        if entry is None or target is None:
            return None
        e, t = float(entry), float(target)
        if e == 0:
            return None
        return round((t - e) / e * 100.0, 4)
    except (TypeError, ValueError):
        return None


def bundle_row_to_master_ticker(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    One summary object per bundle row: entry/exit/targets and bullish profit % to T1/T2/target.
    exit_price is the labeled-window reference close (see backtest_phoenix), not a broker fill.
    """
    err = row.get("error")
    if err:
        return {
            "error": err,
            "fusion_final_signal": None,
            "entry_price": None,
            "exit_price": None,
            "target_t1": None,
            "target_t2": None,
        }

    tl = row.get("trade_levels") or {}
    bt = row.get("backtest") or {}
    entry = tl.get("entry_price")
    if entry is None:
        entry = bt.get("entry_price")
    fus = row.get("fusion_final_signal")
    t1 = tl.get("target_1")
    t2 = tl.get("target_2")
    bt_tgt = bt.get("target_price")
    exit_px = bt.get("exit_reference_price")

    bullish = fus == "bullish"
    profit_t1 = _pct_long(entry, t1) if bullish else None
    profit_t2 = _pct_long(entry, t2) if bullish else None
    profit_bt = _pct_long(entry, bt_tgt) if bullish else None

    out: Dict[str, Any] = {
        "sector": row.get("sector"),
        "fusion_final_signal": fus,
        "fusion_orchestrator_score": row.get("fusion_orchestrator_score"),
        "fusion_conflict": row.get("fusion_conflict"),
        "phoenix_signal": row.get("phoenix_signal"),
        "phoenix_score": row.get("phoenix_score"),
        "fund_score": row.get("fund_score"),
        "entry_price": entry,
        "exit_price": exit_px,
        "exit_reference_date": bt.get("exit_reference_date"),
        "stop_price": tl.get("stop_price"),
        "target_t1": t1,
        "target_t2": t2,
        "backtest_target_price": bt_tgt,
        "profit_pct_to_t1": profit_t1,
        "profit_pct_to_t2": profit_t2,
        "profit_pct_to_backtest_target": profit_bt,
        "hypothetical_long_profit_pct_to_t1": _pct_long(entry, t1),
        "hypothetical_long_profit_pct_to_t2": _pct_long(entry, t2),
        "hypothetical_long_profit_pct_to_backtest_target": _pct_long(entry, bt_tgt),
        "target_hit": bt.get("target_hit"),
        "target_hit_date": bt.get("target_hit_date"),
        "signal_correct": (row.get("evaluation") or {}).get("signal_correct"),
        "pattern_name": tl.get("pattern_name"),
    }
    out["notes"] = (
        "profit_pct_* counts only when fusion_final_signal is bullish (labeled accuracy). "
        "hypothetical_long_profit_pct_* is (target-entry)/entry from listed prices—not trade advice. "
        "exit_price is end-of-eval-window reference when forward data exists."
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Phoenix+FA labeled window backtest — pass either --tickers or --sector "
            "(see module docstring)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --tickers AMAT --signal-date 2025-09-01 --output-dir data/output/trading_runs/amat\n"
            "  %(prog)s --tickers AAPL,MSFT --signal-date 2025-06-01 --workers 2\n"
            '  %(prog)s --sector "Information Technology" --limit 50 --signal-date 2024-12-31\n'
        ),
    )
    uni = parser.add_mutually_exclusive_group(required=True)
    uni.add_argument(
        "--sector",
        metavar="NAME",
        help='Halal sector key from halal_sector_tickers.json (e.g. "Information Technology")',
    )
    uni.add_argument(
        "--tickers",
        metavar="SYM,...",
        help='Comma-separated symbols (one or many), e.g. AMAT or "AAPL,MSFT"',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="With --sector (default mode): take first N names after --offset. Ignored if --full-sector.",
    )
    parser.add_argument(
        "--full-sector",
        action="store_true",
        help="With --sector: use entire sector list (after --offset, capped by --max-tickers).",
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=None,
        metavar="N",
        help="With --full-sector: cap total tickers (e.g. 200 trial).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="With --sector: skip first N symbols in JSON list order.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="Process sector tickers in sequential batches of N; writes batch_XX_results.json checkpoints.",
    )
    parser.add_argument(
        "--random-sample",
        action="store_true",
        help="Draw limit tickers uniformly instead of first N in file order.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--signal-date",
        required=True,
        metavar="YYYY-MM-DD",
        help="As-of date for Phoenix + FA (inputs use data through this day only).",
    )
    parser.add_argument(
        "--eval-days",
        type=int,
        default=30,
        help="Calendar days after signal_date for Polygon target-hit window.",
    )
    parser.add_argument("--period-workers", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4, help="Parallel tickers.")
    parser.add_argument(
        "--output-dir",
        default=str(paths.OUTPUT_DIR / "trading_runs" / "phoenix_fa_window_pilot"),
        help="Directory for run_bundle.json, per_ticker/, manifest, confusion_matrix.",
    )
    parser.add_argument(
        "--single-master-json",
        action="store_true",
        help=(
            "Write only master_pilot.json: manifest, confusion_matrix, and per-ticker trading "
            "fields (entry, exit reference, T1/T2, profit %%). Skips per_ticker shards, "
            "pilot_results.json, run_bundle.json, confusion_matrix.json, batch checkpoints."
        ),
    )
    args = parser.parse_args()

    sig = date.fromisoformat(args.signal_date)
    end = sig + timedelta(days=int(args.eval_days))
    months = [(sig, end)]

    explicit_tickers = args.tickers
    if explicit_tickers:
        tickers = [t.strip().upper() for t in explicit_tickers.split(",") if t.strip()]
        if not tickers:
            raise SystemExit("No symbols after parsing --tickers")
        canon_sector = "explicit_tickers"
        universe_label = f"tickers={','.join(tickers)}"
        batch_plan: Optional[List[List[str]]] = None
    else:
        if args.random_sample:
            canon_sector, tickers = load_sector_tickers(
                args.sector,
                int(args.limit),
                0,
                args.seed,
                True,
            )
        elif args.full_sector or args.max_tickers is not None:
            canon_sector, tickers = load_sector_tickers(
                args.sector,
                args.max_tickers,
                int(args.offset),
                args.seed,
                False,
            )
        else:
            canon_sector, tickers = load_sector_tickers(
                args.sector,
                int(args.limit),
                int(args.offset),
                args.seed,
                False,
            )
        universe_label = f'{canon_sector} n={len(tickers)} halal_sector'

        if args.batch_size is not None:
            bs = max(1, int(args.batch_size))
            batch_plan = [tickers[i : i + bs] for i in range(0, len(tickers), bs)]
        else:
            batch_plan = None

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from lib.run_bundle import load_ticker_sector_map  # noqa: E402

    _sector_by_ticker = load_ticker_sector_map()

    manifest: Dict[str, Any] = {
        "no_lookahead_statement": (
            "Phoenix and Fundamental analyze_ticker calls use as_of_date equal to signal_date only. "
            "OHLCV and fundamentals are restricted to data on or before that date. "
            "Prices after signal_date are used only for outcome labeling (target hit, exit reference close), "
            "never as inputs to the screening models."
        ),
        "signal_date": sig.isoformat(),
        "result_date": end.isoformat(),
        "eval_days": int(args.eval_days),
        "sector": canon_sector,
        "tickers_explicit": bool(args.tickers),
        "universe_label": universe_label,
        "tickers_requested": len(tickers),
        "random_sample": bool(getattr(args, "random_sample", False)),
        "seed": args.seed,
        "full_sector": bool(getattr(args, "full_sector", False)),
        "offset": int(args.offset),
        "max_tickers": args.max_tickers,
        "batch_size": args.batch_size,
        "batches_planned": len(batch_plan) if batch_plan else 1,
        "single_master_json": bool(args.single_master_json),
    }
    if not args.single_master_json:
        (out_dir / "pilot_manifest.json").write_text(json.dumps(manifest, indent=2))

    results: Dict[str, Dict[str, Any]] = {}
    t0 = time.time()
    if batch_plan:
        for bi, batch in enumerate(batch_plan):
            print(
                f"── Batch {bi + 1}/{len(batch_plan)} — {len(batch)} ticker(s) ──",
                flush=True,
            )
            with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
                futs = {
                    pool.submit(_run_ticker, t, months, int(args.period_workers)): t
                    for t in batch
                }
                for fut in as_completed(futs):
                    t = futs[fut]
                    try:
                        results[t] = fut.result()
                    except Exception as exc:
                        results[t] = {"ticker": t, "error": str(exc), "periods": []}
            if not args.single_master_json:
                ck = {
                    "batch_index": bi + 1,
                    "tickers": batch,
                    "results": {t: results[t] for t in batch if t in results},
                }
                (out_dir / f"batch_{bi + 1:02d}_results.json").write_text(
                    json.dumps(ck, indent=2, default=str),
                    encoding="utf-8",
                )
    else:
        with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
            futs = {
                pool.submit(_run_ticker, t, months, int(args.period_workers)): t
                for t in tickers
            }
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    results[t] = fut.result()
                except Exception as exc:
                    results[t] = {"ticker": t, "error": str(exc), "periods": []}

    elapsed = time.time() - t0
    if not args.single_master_json:
        (out_dir / "pilot_results.json").write_text(json.dumps(results, indent=2, default=str))

    from lib.run_bundle import (  # noqa: E402
        build_run_bundle,
        row_from_error,
        row_from_labeled_backtest_period,
        write_bundle,
    )

    bundle_rows: List[Dict[str, Any]] = []
    as_of_str = sig.isoformat()
    run_id = f"halal_pilot_{as_of_str}_{uuid.uuid4().hex[:10]}"

    for tk in tickers:
        r = results.get(tk) or {}
        row_sector = _sector_by_ticker.get(tk.upper()) if args.tickers else canon_sector
        art = f"{tk}_{as_of_str}_phoenix_fa_backtest.json"
        rel = f"per_ticker/{art}"
        per_path = out_dir / "per_ticker" / art
        if not args.single_master_json:
            per_path.parent.mkdir(parents=True, exist_ok=True)
            per_path.write_text(json.dumps(r, indent=2, default=str))

        if r.get("error") and not r.get("periods"):
            bundle_rows.append(
                row_from_error(tk, as_of_str, row_sector, "phoenix-fa", str(r.get("error")))
            )
            continue

        for period in r.get("periods") or []:
            bundle_rows.append(
                row_from_labeled_backtest_period(
                    tk,
                    as_of_str,
                    row_sector,
                    period,
                    rel,
                )
            )

    bundle = build_run_bundle(
        run_id=run_id,
        as_of_date=as_of_str,
        fusion="phoenix-fa",
        universe_label=(
            f"{universe_label} | labeled_backtest signal={as_of_str} "
            f"eval_horizon={int(args.eval_days)}d"
        ),
        fund_data_source="yfinance",
        rows=bundle_rows,
        halal_universe_mode="full",
    )
    bundle["pilot_meta"] = {**manifest, "elapsed_sec": round(elapsed, 2)}
    if args.single_master_json:
        bp = out_dir / "master_pilot.json"
    else:
        bp = write_bundle(out_dir, bundle)

    rows_flat: List[Dict[str, Any]] = []
    for tk in tickers:
        r = results.get(tk) or {}
        sec_flat = _sector_by_ticker.get(tk.upper()) if args.tickers else canon_sector
        for p in r.get("periods") or []:
            rows_flat.append({**p, "ticker": tk, "sector": sec_flat})
    df = pd.DataFrame(rows_flat)
    cm = _confusion_target_hit(df) if not df.empty else {}
    cm_payload = {
        "meta": {
            "description": "Fusion directional signal vs target-hit correctness (see backtest_phoenix).",
            "elapsed_sec": round(elapsed, 2),
            "tickers": len(tickers),
            "primary_artifact": (
                "master_pilot.json" if args.single_master_json else str(bp.name)
            ),
        },
        "cumulative": {"overall": cm},
    }
    if not args.single_master_json:
        (out_dir / "confusion_matrix.json").write_text(json.dumps(cm_payload, indent=2))

    master_tickers = {str(r["ticker"]).upper(): bundle_row_to_master_ticker(r) for r in bundle_rows}

    if args.single_master_json:
        master_doc: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "manifest": manifest,
            "confusion_matrix": cm_payload,
            "tickers": master_tickers,
            "elapsed_sec": round(elapsed, 2),
        }
        bp.write_text(json.dumps(master_doc, indent=2, default=str), encoding="utf-8")

    print()
    print("=" * 72)
    print(f"Pilot done in {elapsed:.1f}s")
    print(f"Universe: {universe_label} | Tickers: {len(tickers)}")
    print(f"Signal / eval window: {sig} → {end} ({int(args.eval_days)} calendar days)")
    if args.single_master_json:
        print(f"master_pilot.json → {bp}")
    else:
        print(f"run_bundle.json → {bp}")
    print(f"Confusion (overall): {cm}")
    print("=" * 72)


if __name__ == "__main__":
    main()
