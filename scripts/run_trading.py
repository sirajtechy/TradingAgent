#!/usr/bin/env python3
"""
run_trading.py — Canonical CLI for analysis and backtest delegation.

Design goals (see MODULE_MAP.md):
  • One entry point so prompts add flags here instead of new scripts.
  • Phoenix + Fundamental CWAF is the primary fusion path (--fusion phoenix-fa).
  • Legacy TA + FA remains (--fusion ta-fa).

Examples
────────
  # Phoenix + Fundamental (orchestrator fusion over Phoenix slot + FA)
  python scripts/run_trading.py analyze --date 2026-04-30 --fusion phoenix-fa \\
      --tickers CRWD,AMD

  # Halal sector (Musaffa universe), top 10 per sector list
  python scripts/run_trading.py analyze --date 2026-04-30 --fusion phoenix-fa \\
      --halal-sector "Energy" --halal-limit 10

  # Random sample of 8 tickers across two halal sectors
  python scripts/run_trading.py analyze --date 2026-04-30 --fusion phoenix-fa \\
      --halal-sectors "Energy,Technology" --random-sample 8

  # Legacy 5-sector universe (non-halal mix)
  python scripts/run_trading.py analyze --date 2026-04-30 --fusion ta-fa \\
      --sector Technology

  # Delegate heavy monthly backtest to existing engine (do not duplicate logic)
  python scripts/run_trading.py backtest --engine halal-orchestrator-2025 -- \\
      --sector Energy --months 2
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent

# ── Registry: one stable name → script path (heavy runners stay in place) ─────
BACKTEST_ENGINES: Dict[str, Path] = {
    "halal-orchestrator-2025": ROOT / "scripts" / "backtests" / "run_halal_orchestrator_backtest_2025.py",
    "halal-sector-pilot": ROOT / "scripts" / "backtests" / "run_halal_sector_month_pilot.py",
    "phoenix-fund-2025": ROOT / "scripts" / "backtests" / "run_phoenix_fund_orchestrator_backtest_2025.py",
    "phoenix-orchestrator-2025": ROOT / "scripts" / "backtests" / "run_phoenix_orchestrator_backtest_2025.py",
    "orchestrator-legacy": ROOT / "scripts" / "backtests" / "run_orchestrator_backtest.py",
    "sector-legacy": ROOT / "scripts" / "backtests" / "run_sector_backtest.py",
}


def _validate_date_iso(d: str) -> str:
    datetime.strptime(d, "%Y-%m-%d")
    return d


def _parse_tickers(raw: str) -> List[str]:
    parts = [p.strip().upper() for p in raw.split(",")]
    return [p for p in parts if p]


def _fusion_to_dict(fr: Any) -> Dict[str, Any]:
    return dataclasses.asdict(fr)


def _halal_sector_map(args: argparse.Namespace) -> Dict[str, List[str]]:
    """top10 = curated list in backtests.common; full = entire sector from JSON."""
    sys.path.insert(0, str(ROOT))
    mode = getattr(args, "halal_universe", "top10")
    if mode == "full":
        from data.halal_universe import load_sector_tickers  # noqa: E402

        return load_sector_tickers()
    from backtests.common import HALAL_SECTORS  # noqa: E402

    return HALAL_SECTORS


def resolve_universe(args: argparse.Namespace) -> Tuple[List[str], str]:
    """
    Returns (tickers, human-readable label).
    Exactly one universe mode must be selected by the caller (enforced in argparse).
    """
    if getattr(args, "tickers", None):
        t = _parse_tickers(args.tickers)
        if not t:
            raise SystemExit("No tickers after parsing --tickers")
        return t, f"tickers={len(t)}"

    if getattr(args, "sector", None):
        sys.path.insert(0, str(ROOT))
        from backtests.common import SECTORS  # noqa: E402

        if args.sector not in SECTORS:
            raise SystemExit(
                f'Unknown legacy sector "{args.sector}". '
                f'Valid: {", ".join(sorted(SECTORS.keys()))}'
            )
        tickers = list(SECTORS[args.sector])
        return tickers, f'legacy sector="{args.sector}" ({len(tickers)} tkrs)'

    if getattr(args, "halal_sector", None):
        halal = _halal_sector_map(args)

        sec = args.halal_sector.strip()
        # Allow fuzzy case
        keys = {k.lower(): k for k in halal.keys()}
        if sec.lower() not in keys:
            sample = ", ".join(sorted(halal.keys())[:10])
            raise SystemExit(
                f'Unknown halal sector "{sec}". '
                f'Examples: {sample} … ({len(halal)} sectors)'
            )
        canon = keys[sec.lower()]
        tickers = list(halal[canon])
        lim = getattr(args, "halal_limit", None)
        if lim is not None:
            tickers = tickers[: int(lim)]
        uni = getattr(args, "halal_universe", "top10")
        return tickers, f'halal sector="{canon}" uni={uni} ({len(tickers)} tkrs)'

    if getattr(args, "halal_sectors", None):
        halal = _halal_sector_map(args)

        raw_secs = [s.strip() for s in args.halal_sectors.split(",") if s.strip()]
        keys_lower = {k.lower(): k for k in halal.keys()}
        pool: List[str] = []
        for s in raw_secs:
            if s.lower() not in keys_lower:
                raise SystemExit(f'Unknown halal sector "{s}"')
            pool.extend(halal[keys_lower[s.lower()]])
        pool = list(dict.fromkeys(pool))
        n = int(args.random_sample)
        if n > len(pool):
            raise SystemExit(f"--random-sample {n} > union pool size {len(pool)}")
        rng = random.Random(getattr(args, "seed", None) or 42)
        picked = rng.sample(pool, n)
        uni = getattr(args, "halal_universe", "top10")
        label = (
            f"random {n} from sectors [{args.halal_sectors}] uni={uni} "
            f"seed={getattr(args, 'seed', 42)}"
        )
        return picked, label

    raise AssertionError("resolve_universe: no mode")


def run_analyze(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    from lib.run_bundle import (  # noqa: E402
        build_run_bundle,
        load_ticker_sector_map,
        row_from_compare,
        row_from_error,
        row_from_phoenix_fund,
        row_from_phoenix_only,
        row_from_ta_fa,
        write_bundle,
    )

    as_of = _validate_date_iso(args.date)
    tickers, label = resolve_universe(args)

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fusion = args.fusion
    bundle_rows: List[Dict[str, Any]] = []
    sector_map = load_ticker_sector_map()

    def sec_for(tk: str) -> Optional[str]:
        return sector_map.get(tk.upper())

    print(
        f"\nrun_trading analyze — fusion={fusion} — {len(tickers)} ticker(s) "
        f"({label}) @ {as_of}\n"
        + "─" * 62
    )

    from agents.orchestrator.config import OrchestratorSettings  # noqa: E402
    from agents.orchestrator.modes import FusionMode, fuse_by_mode  # noqa: E402

    cfg = OrchestratorSettings(fund_data_source=args.fund_data_source)

    if fusion == "ta-fa":
        from agents.orchestrator.service import analyze_ticker as orch_analyze  # noqa: E402

        for t in tickers:
            art = f"{t}_{as_of}_orchestrator_ta_fa.json"
            try:
                result = orch_analyze(ticker=t, as_of_date=as_of, settings=cfg)
                _print_ta_fa_line(t, result)
                (out_dir / art).write_text(json.dumps(result, indent=2, default=str))
                bundle_rows.append(
                    row_from_ta_fa(t, as_of, sec_for(t), result, art)
                )
            except Exception as exc:
                print(f"[TA+FA] {t:<6} ERROR: {exc}")
                bundle_rows.append(
                    row_from_error(t, as_of, sec_for(t), "ta-fa", str(exc))
                )

    elif fusion == "phoenix":
        from agents.phoenix.service import analyze_ticker as phoenix_analyze  # noqa: E402

        for t in tickers:
            art = f"{t}_{as_of}_phoenix.json"
            try:
                px = phoenix_analyze(ticker=t, as_of_date=as_of)
                _print_phoenix_line(t, px)
                if len(tickers) == 1:
                    print("\n" + (px.get("report") or ""))
                (out_dir / art).write_text(json.dumps(px, indent=2, default=str))
                bundle_rows.append(row_from_phoenix_only(t, as_of, sec_for(t), px, art))
            except Exception as exc:
                print(f"[PHX]   {t:<6} ERROR: {exc}")
                bundle_rows.append(
                    row_from_error(t, as_of, sec_for(t), "phoenix", str(exc))
                )

    elif fusion == "phoenix-fa":
        from agents.fundamental.service import analyze_ticker as fund_analyze  # noqa: E402
        from agents.phoenix.service import analyze_ticker as phoenix_analyze  # noqa: E402

        for t in tickers:
            art = f"{t}_{as_of}_phoenix_fund.json"
            try:
                px = phoenix_analyze(ticker=t, as_of_date=as_of)
                fund = fund_analyze(
                    ticker=t,
                    as_of_date=as_of,
                    data_source=cfg.fund_data_source,
                )
                fus = fuse_by_mode(
                    FusionMode.PHOENIX_FUND,
                    phoenix_result=px,
                    phoenix_error=None,
                    fund_result=fund,
                    fund_error=None,
                    settings=cfg,
                )
                _print_phoenix_fa_line(t, fus)
                payload = {
                    "ticker": t,
                    "as_of_date": as_of,
                    "fusion": _fusion_to_dict(fus),
                    "phoenix": px,
                    "fundamental": fund,
                }
                (out_dir / art).write_text(json.dumps(payload, indent=2, default=str))
                bundle_rows.append(
                    row_from_phoenix_fund(t, as_of, sec_for(t), payload, art)
                )
            except Exception as exc:
                print(f"[PX+FA] {t:<6} ERROR: {exc}")
                bundle_rows.append(
                    row_from_error(t, as_of, sec_for(t), "phoenix-fa", str(exc))
                )

    elif fusion == "compare":
        from agents.orchestrator.service import analyze_ticker as orch_analyze  # noqa: E402
        from agents.phoenix.service import analyze_ticker as phoenix_analyze  # noqa: E402

        for t in tickers:
            art_ta = f"{t}_{as_of}_orchestrator_ta_fa.json"
            art_px = f"{t}_{as_of}_phoenix.json"
            result: Dict[str, Any] = {}
            px: Dict[str, Any] = {}
            try:
                result = orch_analyze(ticker=t, as_of_date=as_of, settings=cfg)
                _print_ta_fa_line(t, result)
                (out_dir / art_ta).write_text(json.dumps(result, indent=2, default=str))
            except Exception as exc:
                print(f"[TA+FA] {t:<6} ERROR: {exc}")
            try:
                px = phoenix_analyze(ticker=t, as_of_date=as_of)
                _print_phoenix_line(t, px)
                if len(tickers) == 1:
                    print("\n" + (px.get("report") or ""))
                (out_dir / art_px).write_text(json.dumps(px, indent=2, default=str))
            except Exception as exc:
                print(f"[PHX]   {t:<6} ERROR: {exc}")
            if result or px:
                bundle_rows.append(
                    row_from_compare(t, as_of, sec_for(t), result, px, art_ta, art_px)
                )

    if not getattr(args, "skip_bundle", False):
        run_id = getattr(args, "run_label", None) or f"{as_of}_{uuid.uuid4().hex[:10]}"
        bundle = build_run_bundle(
            run_id=run_id,
            as_of_date=as_of,
            fusion=fusion,
            universe_label=label,
            fund_data_source=args.fund_data_source,
            rows=bundle_rows,
            halal_universe_mode=getattr(args, "halal_universe", None),
        )
        bp = write_bundle(out_dir, bundle)
        print(f"\nrun_bundle.json (schema {bundle['schema_version']}) → {bp.relative_to(ROOT)}")

    print(f"\nOutputs → {out_dir}\n")


def _print_ta_fa_line(t: str, result: Dict[str, Any]) -> None:
    score = result.get("orchestrator_score")
    conf = result.get("final_confidence")
    sig = result.get("final_signal")
    conflict = bool(result.get("conflict_detected"))
    tech = result.get("tech_output") or {}
    fund = result.get("fund_output") or {}
    ta_s = tech.get("score")
    fa_s = fund.get("score")
    score_s = f"{score:.1f}" if isinstance(score, (int, float)) else "N/A"
    conf_s = f"{conf:.0%}" if isinstance(conf, (int, float)) else "N/A"
    ta_s_s = f"{ta_s:.1f}" if isinstance(ta_s, (int, float)) else "N/A"
    fa_s_s = f"{fa_s:.1f}" if isinstance(fa_s, (int, float)) else "N/A"
    print(
        f"[TA+FA] {t:<6} signal={str(sig).upper():<7} score={score_s:>5} "
        f"conf={conf_s:>4} TA={ta_s_s:>5} FA={fa_s_s:>5} conflict={conflict}"
    )


def _print_phoenix_line(t: str, px: Dict[str, Any]) -> None:
    px_sig = px.get("signal", "N/A")
    px_score = px.get("score", 0)
    px_stage = (px.get("stage") or {}).get("stage", "?")
    px_pat = (px.get("pattern") or {}).get("pattern_name", "None")
    px_conf = (px.get("pattern") or {}).get("confirmed", False)
    px_filt = "PASS" if px.get("hard_filter_passed") else "FAIL"
    px_score_s = f"{px_score:.1f}" if isinstance(px_score, (int, float)) else "N/A"
    print(
        f"[PHX]   {t:<6} signal={px_sig:<7} score={px_score_s:>5} "
        f"stage={px_stage} pattern={px_pat:<12} confirmed={str(px_conf):<5} filter={px_filt}"
    )


def _print_phoenix_fa_line(t: str, fus: Any) -> None:
    sig = fus.final_signal
    score = fus.orchestrator_score
    conf = fus.final_confidence
    cx = fus.conflict_detected
    score_s = f"{score:.1f}" if isinstance(score, (int, float)) else "N/A"
    conf_s = f"{conf:.0%}" if isinstance(conf, (int, float)) else "N/A"
    print(
        f"[PX+FA] {t:<6} signal={str(sig).upper():<7} score={score_s:>5} "
        f"conf={conf_s:>4} conflict={cx}"
    )


def run_compare_cli(args: argparse.Namespace) -> None:
    """Emit comparison JSON from two run_bundle.json files (stable UI delta feed)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from lib.run_bundle import compare_bundles, load_bundle, write_compare  # noqa: E402

    pa = Path(args.bundle_a)
    pb = Path(args.bundle_b)
    if not pa.is_absolute():
        pa = ROOT / pa
    if not pb.is_absolute():
        pb = ROOT / pb
    out = Path(args.compare_out)
    if not out.is_absolute():
        out = ROOT / out

    a = load_bundle(pa)
    b = load_bundle(pb)
    cmp_doc = compare_bundles(a, b)
    write_compare(out, cmp_doc)
    print(f"Wrote comparison ({cmp_doc['summary']}) → {out.relative_to(ROOT)}")


def run_backtest(args: argparse.Namespace) -> None:
    engine = args.engine
    if engine not in BACKTEST_ENGINES:
        raise SystemExit(f"Unknown engine {engine!r}. Choices: {list(BACKTEST_ENGINES)}")
    script = BACKTEST_ENGINES[engine]
    if not script.is_file():
        raise SystemExit(f"Missing script: {script}")

    cmd = [sys.executable, str(script)] + list(args.remainder)
    print("Delegating to:", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Canonical trading analysis / backtest delegation CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See docstring for examples. Prefer this script over adding new runners.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ── analyze ─────────────────────────────────────────────────────────────
    pa = sub.add_parser("analyze", help="Point-in-time analysis (Polygon/network as agents need)")
    pa.add_argument("--date", required=True, help="Cutoff YYYY-MM-DD (no lookahead)")
    pa.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "ta-fa", "phoenix", "compare"],
        help=(
            "phoenix-fa = CWAF Phoenix + Fundamental (primary orchestration path); "
            "ta-fa = LangGraph TA+FA; phoenix = Phoenix only; compare = TA+FA and Phoenix side-by-side"
        ),
    )
    pa.add_argument(
        "--fund-data-source",
        default="yfinance",
        choices=["yfinance", "fmp"],
        help="Passed to Fundamental agent / OrchestratorSettings",
    )
    pa.add_argument(
        "--output-dir",
        default="data/output/trading_runs",
        help="JSON output directory (under repo root)",
    )

    uni = pa.add_mutually_exclusive_group(required=True)
    uni.add_argument("--tickers", help='Comma-separated tickers, e.g. "AAPL,MSFT"')
    uni.add_argument(
        "--sector",
        help='Legacy 5-sector universe key (backtests/common.SECTORS), e.g. "Technology"',
    )
    uni.add_argument(
        "--halal-sector",
        help="Single Musaffa halal sector name (see HALAL_SECTORS keys)",
    )
    uni.add_argument(
        "--halal-sectors",
        help='Comma-separated halal sectors; use with --random-sample (union pool)',
    )

    pa.add_argument(
        "--halal-universe",
        default="top10",
        choices=["top10", "full"],
        help=(
            "top10 = built-in short list per sector; "
            "full = all tickers in sector from data/halal_universe/halal_sector_tickers.json "
            "(best with --halal-limit N, e.g. 100)"
        ),
    )
    pa.add_argument(
        "--halal-limit",
        type=int,
        default=None,
        help="With --halal-sector: take first N tickers from the sector list (list order = JSON order)",
    )
    pa.add_argument(
        "--random-sample",
        type=int,
        default=None,
        help="With --halal-sectors: pick this many tickers uniformly without replacement",
    )
    pa.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed for --random-sample",
    )
    pa.add_argument(
        "--run-label",
        default=None,
        help="Stable run_id stored inside run_bundle.json (default: date + short uuid)",
    )
    pa.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Do not write run_bundle.json (only per-ticker JSON files)",
    )
    pa.set_defaults(func=run_analyze)

    pc = sub.add_parser(
        "compare",
        help="Compare two run_bundle.json files and write a delta JSON for UI",
    )
    pc.add_argument("--bundle-a", required=True, help="Path to first run_bundle.json")
    pc.add_argument("--bundle-b", required=True, help="Path to second run_bundle.json")
    pc.add_argument(
        "--out",
        dest="compare_out",
        required=True,
        help="Output path for comparison JSON (e.g. data/output/trading_runs/deltas/run_vs_run.json)",
    )
    pc.set_defaults(func=run_compare_cli)

    # ── backtest ────────────────────────────────────────────────────────────
    pb = sub.add_parser(
        "backtest",
        help="Run a registered long-form backtest script (pass-through after --)",
    )
    pb.add_argument(
        "--engine",
        required=True,
        choices=sorted(BACKTEST_ENGINES.keys()),
        help="Stable alias for scripts/backtests/*.py heavy runners",
    )
    pb.add_argument(
        "remainder",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the engine (typically after -- )",
    )
    pb.set_defaults(func=run_backtest)

    return p


def validate_analyze_args(args: argparse.Namespace) -> None:
    if args.halal_sectors:
        if args.random_sample is None:
            raise SystemExit("--halal-sectors requires --random-sample N")
    elif args.random_sample is not None:
        raise SystemExit("--random-sample only applies with --halal-sectors")


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        validate_analyze_args(args)
    elif args.command == "compare":
        pass
    args.func(args)


if __name__ == "__main__":
    main()
