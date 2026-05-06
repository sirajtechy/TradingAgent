#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _parse_tickers(raw: str) -> List[str]:
    parts = [p.strip().upper() for p in raw.split(",")]
    tickers = [p for p in parts if p]
    if not tickers:
        raise ValueError("No tickers provided. Example: --tickers AAPL,MSFT")
    return tickers


def _validate_date_iso(d: str) -> str:
    # Enforce YYYY-MM-DD so you don't accidentally run "latest".
    datetime.strptime(d, "%Y-%m-%d")
    return d


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run trading analysis for either explicit tickers OR a sector "
            "at a required cutoff date. Supports --strategy flag to choose "
            "orchestrator (TA+FA), phoenix, or both."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tickers",
        help='Comma-separated tickers, e.g. "AAPL,MSFT,NVDA" (supports 1 ticker too)',
    )
    group.add_argument(
        "--sector",
        help='Sector name as defined in backtests/common.py (e.g. "Technology")',
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Cutoff date (YYYY-MM-DD). Required to avoid accidental lookahead.",
    )
    parser.add_argument(
        "--strategy",
        default="orchestrator",
        choices=["orchestrator", "phoenix", "both"],
        help=(
            "Which strategy to run: "
            "'orchestrator' (TA+FA, default), "
            "'phoenix' (@pheonix_trader strategy), "
            "or 'both' (run side-by-side)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="data/output/orchestrator_runs",
        help="Directory to write JSON results into.",
    )
    args = parser.parse_args()

    as_of_date = _validate_date_iso(args.date)

    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    if args.tickers:
        tickers = _parse_tickers(args.tickers)
        run_label = "tickers"
    else:
        from backtests.common import SECTORS  # noqa: E402

        if args.sector not in SECTORS:
            valid = ", ".join(sorted(SECTORS.keys()))
            raise SystemExit(f'Unknown sector "{args.sector}". Valid: {valid}')
        tickers = list(SECTORS[args.sector])
        run_label = f'sector="{args.sector}"'

    out_dir = repo_root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    strategy = args.strategy

    print(f"\nStrategy: {strategy.upper()} — {len(tickers)} ticker(s) ({run_label}) @ {as_of_date}")
    print("──────────────────────────────────────────────────────────────")

    if strategy in ("orchestrator", "both"):
        from agents.orchestrator.service import analyze_ticker as orch_analyze  # noqa: E402

    if strategy in ("phoenix", "both"):
        from agents.phoenix.service import analyze_ticker as phoenix_analyze  # noqa: E402

    for t in tickers:

        # ── Orchestrator (TA + FA) ─────────────────────────────────────
        if strategy in ("orchestrator", "both"):
            try:
                result: Dict[str, Any] = orch_analyze(ticker=t, as_of_date=as_of_date)

                score    = result.get("orchestrator_score")
                conf     = result.get("final_confidence")
                sig      = result.get("final_signal")
                conflict = bool(result.get("conflict_detected"))

                score_s = f"{score:.1f}" if isinstance(score, (int, float)) else "N/A"
                conf_s  = f"{conf:.0%}"  if isinstance(conf,  (int, float)) else "N/A"

                tech   = result.get("tech_output") or {}
                fund   = result.get("fund_output") or {}
                ta_s   = tech.get("score")
                fa_s   = fund.get("score")
                ta_s_s = f"{ta_s:.1f}" if isinstance(ta_s, (int, float)) else "N/A"
                fa_s_s = f"{fa_s:.1f}" if isinstance(fa_s, (int, float)) else "N/A"

                print(
                    f"[ORCH]  {t:<6}  signal={str(sig).upper():<7}  score={score_s:>5}  "
                    f"conf={conf_s:>4}  TA={ta_s_s:>5}  FA={fa_s_s:>5}  conflict={conflict}"
                )

                out_path = out_dir / f"{t}_{as_of_date}_orchestrator.json"
                out_path.write_text(json.dumps(result, indent=2, default=str))
            except Exception as exc:
                print(f"[ORCH]  {t:<6}  ERROR: {exc}")

        # ── Phoenix Agent ──────────────────────────────────────────────
        if strategy in ("phoenix", "both"):
            try:
                px: Dict[str, Any] = phoenix_analyze(ticker=t, as_of_date=as_of_date)

                px_sig   = px.get("signal", "N/A")
                px_score = px.get("score", 0)
                px_stage = (px.get("stage") or {}).get("stage", "?")
                px_pat   = (px.get("pattern") or {}).get("pattern_name", "None")
                px_conf  = (px.get("pattern") or {}).get("confirmed", False)
                px_filt  = "PASS" if px.get("hard_filter_passed") else "FAIL"

                px_score_s = f"{px_score:.1f}" if isinstance(px_score, (int, float)) else "N/A"
                print(
                    f"[PHOE]  {t:<6}  signal={px_sig:<7}  score={px_score_s:>5}  "
                    f"stage={px_stage}  pattern={px_pat:<12}  confirmed={str(px_conf):<5}  filter={px_filt}"
                )

                # Print full report for single-ticker runs
                if len(tickers) == 1:
                    print()
                    print(px.get("report", ""))

                out_path = out_dir / f"{t}_{as_of_date}_phoenix.json"
                out_path.write_text(json.dumps(px, indent=2, default=str))
            except Exception as exc:
                print(f"[PHOE]  {t:<6}  ERROR: {exc}")

    print("\nOutputs written to:", str(out_dir))
    print("")


if __name__ == "__main__":
    main()
