#!/usr/bin/env python3
"""
MyTradingSpace control plane — single entry for dashboard, backtests, and analyze.

Prefer: ./bin/mts <command>
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT / "apps" / "backtest-dashboard"
LOG_DIR = ROOT / "data" / "output" / "trading_runs" / "logs"
PID_DIR = ROOT / "data" / "output" / ".mts"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def _python() -> str:
    env = os.environ.get("MYTRADING_PYTHON")
    if env and Path(env).is_file():
        return env
    venv = ROOT / ".venv" / "bin" / "python"
    if venv.is_file():
        return str(venv)
    return sys.executable


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _pid_file(port: int) -> Path:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    return PID_DIR / f"dashboard-{port}.pid"


def _read_pid(port: int) -> Optional[int]:
    pf = _pid_file(port)
    if not pf.is_file():
        return None
    try:
        return int(pf.read_text().strip())
    except (OSError, ValueError):
        return None


def _write_pid(port: int, pid: int) -> None:
    _pid_file(port).write_text(str(pid))


def _clear_pid(port: int) -> None:
    pf = _pid_file(port)
    if pf.is_file():
        pf.unlink(missing_ok=True)


def _kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def _kill_port_listeners(port: int) -> None:
    try:
        r = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in (r.stdout or "").strip().splitlines():
            if line.strip().isdigit():
                _kill_pid(int(line.strip()))
    except FileNotFoundError:
        pass


def _start_dashboard_background(port: int) -> None:
    if _port_open(port):
        print(f"Dashboard already listening on http://localhost:{port}")
        return
    if not DASHBOARD_DIR.is_dir():
        raise SystemExit(f"Dashboard not found: {DASHBOARD_DIR}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"mts-dashboard-{port}.log"
    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(DASHBOARD_DIR),
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        print(build.stderr or build.stdout, file=sys.stderr)
        raise SystemExit("Dashboard build failed — run: cd apps/backtest-dashboard && npm run build")
    with open(log_path, "a", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            ["npm", "run", "start", "--", "-p", str(port)],
            cwd=str(DASHBOARD_DIR),
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _write_pid(port, proc.pid)
    for _ in range(30):
        if _port_open(port):
            print(f"Dashboard → http://localhost:{port}")
            print(f"  Research Lab     → http://localhost:{port}/research")
            print(f"  Phoenix pilot    → http://localhost:{port}/research/phoenix")
            print(f"  Signals          → http://localhost:{port}/research/signals")
            print(f"  Log: {log_path}")
            return
        time.sleep(0.5)
    print(f"Dashboard starting (pid {proc.pid}); log: {log_path}")


def cmd_dashboard(args: argparse.Namespace) -> int:
    port = int(args.port)
    if args.background:
        _start_dashboard_background(port)
        return 0
    if not DASHBOARD_DIR.is_dir():
        raise SystemExit(f"Dashboard not found: {DASHBOARD_DIR}")
    print(f"Starting dashboard on http://localhost:{port} (Ctrl+C to stop)")
    return subprocess.call(
        ["npm", "run", "dev", "--", "-p", str(port)],
        cwd=str(DASHBOARD_DIR),
    )


def cmd_stop(args: argparse.Namespace) -> int:
    port = int(args.port)
    pid = _read_pid(port)
    if pid:
        _kill_pid(pid)
        _clear_pid(port)
    _kill_port_listeners(port)
    print(f"Stopped dashboard on port {port}")
    return 0


def _pipeline_argv(command: str, args: argparse.Namespace) -> List[str]:
    py = _python()
    base = [py, "-m", "pipelines", command]
    if command == "analyze":
        if getattr(args, "watchlist", False):
            base.append("--watchlist")
        elif getattr(args, "ticker", None):
            base.extend(["--ticker", args.ticker])
        if args.date:
            base.extend(["--date", args.date])
        base.extend(
            [
                "--fusion",
                args.fusion,
                "--fund-data-source",
                args.fund_data_source,
            ]
        )
        if getattr(args, "watchlist", False):
            if getattr(args, "trade_focus", False):
                base.append("--trade-focus")
            if getattr(args, "max_tickers", None):
                base.extend(["--max-tickers", str(args.max_tickers)])
            if getattr(args, "force", False):
                base.append("--force")
        if getattr(args, "export_breakdown", False):
            base.append("--export-breakdown")
        if getattr(args, "markdown_out", None):
            base.extend(["--markdown-out", str(args.markdown_out)])
        if getattr(args, "json_out", None):
            base.extend(["--json-out", str(args.json_out)])
        if getattr(args, "refresh_context", False):
            base.append("--refresh-context")
        if getattr(args, "strategy_profile", "none") != "none":
            base.extend(["--strategy-profile", args.strategy_profile])
    elif command == "sector":
        base.extend(
            [
                "--sector",
                args.sector,
                "--signal-date",
                args.date,
                "--eval-days",
                str(args.eval_days),
            ]
        )
    elif command == "unified":
        base.extend(
            [
                "--signal-date",
                args.date,
                "--eval-days",
                str(args.eval_days),
                "--sector-jobs",
                str(args.sector_jobs),
                "--workers",
                str(args.workers),
                "--period-workers",
                str(args.period_workers),
            ]
        )
    elif command == "daily":
        base.extend(["--signal-date", args.date, "--eval-days", str(args.eval_days)])
        if args.no_export_buy:
            base.append("--no-export-buy")
        if args.no_telegram:
            base.append("--no-telegram")
    return base


def cmd_export_breakdown(args: argparse.Namespace) -> int:
    import json

    from agents.orchestrator.agent_breakdown import export_agent_breakdown_markdown

    src = args.from_json
    if not src.is_absolute():
        src = ROOT / src
    doc = json.loads(src.read_text(encoding="utf-8"))
    out = args.output
    if out is not None and not out.is_absolute():
        out = ROOT / out
    path = export_agent_breakdown_markdown(doc, out)
    try:
        print(str(path.relative_to(ROOT)))
    except ValueError:
        print(str(path))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    return subprocess.call(_pipeline_argv("analyze", args), cwd=str(ROOT))


def cmd_strategy(args: argparse.Namespace) -> int:
    from agents.strategies.service import analyze_strategies

    as_of = args.date or (date.today() - timedelta(days=1)).isoformat()
    doc = analyze_strategies(ticker=args.ticker, as_of_date=as_of, profile=args.profile)
    print(json.dumps(doc, indent=2, default=str))
    return 0 if doc.get("ok") else 1


def cmd_portfolio_backtest(args: argparse.Namespace) -> int:
    from agents.portfolio.service import backtest_portfolio, write_backtest_outputs

    end = args.end or _default_yesterday()
    result = backtest_portfolio(
        start=args.start,
        end=end,
        budget=float(args.budget),
        universe_mode=args.universe,
        num_stocks=int(args.num_stocks),
        enrich_agents=bool(args.enrich_agents),
        full_agents=bool(getattr(args, "full_agents", False)),
        strategy_profile=args.strategy_profile,
        enrich_max=_resolve_enrich_max(args),
        enrich_workers=int(args.enrich_workers),
        write_outputs=not args.no_write,
    )
    if not args.no_write:
        out_dir = write_backtest_outputs(result)
        print(f"Run ID: {result.run_id}")
        print(f"Output: {out_dir.relative_to(ROOT)}")
    print(json.dumps(result.summary, indent=2))
    if result.warnings:
        print("Warnings:", "; ".join(result.warnings), file=sys.stderr)
    return 0


def cmd_portfolio_allocate(args: argparse.Namespace) -> int:
    from agents.portfolio.service import allocate_portfolio

    as_of = args.date or _default_yesterday()
    doc = allocate_portfolio(
        as_of=as_of,
        budget=float(args.budget),
        universe_mode=args.universe,
        num_stocks=int(args.num_stocks),
        enrich_agents=not args.no_enrich,
        full_agents=bool(getattr(args, "full_agents", False)),
        strategy_profile=args.strategy_profile,
        enrich_max=_resolve_enrich_max(args),
        enrich_workers=int(args.enrich_workers),
    )
    print(json.dumps(doc, indent=2, default=str))
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    if args.portfolio_cmd == "backtest":
        return cmd_portfolio_backtest(args)
    if args.portfolio_cmd == "allocate":
        return cmd_portfolio_allocate(args)
    raise SystemExit(f"Unknown portfolio command: {args.portfolio_cmd}")


def cmd_sector(args: argparse.Namespace) -> int:
    return subprocess.call(_pipeline_argv("sector", args), cwd=str(ROOT))


def cmd_unified(args: argparse.Namespace) -> int:
    return subprocess.call(_pipeline_argv("unified", args), cwd=str(ROOT))


def cmd_daily(args: argparse.Namespace) -> int:
    return subprocess.call(_pipeline_argv("daily", args), cwd=str(ROOT))


def cmd_export(args: argparse.Namespace) -> int:
    from core.io.export import DEFAULT_JSON, DEFAULT_XLSX, export_signals

    d1 = date.fromisoformat(args.date_to) if args.date_to else date.fromisoformat(_default_yesterday())
    d0 = (
        date.fromisoformat(args.date_from)
        if args.date_from
        else (d1 - timedelta(days=int(args.lookback_days)))
    )
    sigs = [s.strip() for s in args.signals.split(",") if s.strip()]
    out_xlsx = args.output
    if not out_xlsx.is_absolute():
        out_xlsx = ROOT / out_xlsx
    out_json = args.json_output
    if out_json is None:
        out_json = DEFAULT_JSON
    elif not out_json.is_absolute():
        out_json = ROOT / out_json

    result = export_signals(
        date_from=d0,
        date_to=d1,
        signals=sigs,
        include_archive=not args.no_archive,
        output_xlsx=out_xlsx if not args.json_only else None,
        output_json=out_json,
        write_excel=not args.json_only,
        write_json=True,
    )
    s = result.summary
    print(f"Date range: {s.get('date_from')} → {s.get('date_to')}")
    print(f"Sources scanned: {s.get('sources_scanned')}")
    print(f"Signals (deduped): {s.get('signals_deduped')} (BUY={s.get('buy')}, WATCH={s.get('watch')})")
    if not args.json_only:
        print(f"Excel → {out_xlsx.relative_to(ROOT)}")
    print(f"JSON  → {out_json.relative_to(ROOT)}")
    print(f"Dashboard → http://localhost:3055/research/signals")
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    from agents._registry import analyze_and_envelope

    agent_id = args.agent_id.strip().lower()
    as_of = args.date
    ticker = args.ticker or ""
    try:
        native, envelope = analyze_and_envelope(
            agent_id,
            ticker=ticker,
            as_of_date=as_of,
        )
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    except Exception as exc:
        raise SystemExit(f"Agent {agent_id!r} failed: {exc}") from exc

    payload = {"native": native, "envelope": envelope}
    if args.envelope_only:
        payload = envelope
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    from agents._registry import analyze_and_envelope

    as_of = args.date
    out_dir = ROOT / "data" / "output" / "context"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"context_{as_of}.json"

    session_agents = ["macro", "market_summary", "geopolitics"]
    result: dict = {"as_of_date": as_of, "agents": {}}
    for agent_id in session_agents:
        native, envelope = analyze_and_envelope(agent_id, ticker="", as_of_date=as_of)
        result["agents"][agent_id] = {"native": native, "envelope": envelope}

    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"\nWrote → {out_path.relative_to(ROOT)}")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    py = _python()
    if args.loop_cmd == "cycle":
        cmd = ["bash", str(ROOT / "scripts" / "loop_run_cycle.sh")]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.feature:
            cmd.extend(["--feature", args.feature])
        return subprocess.call(cmd, cwd=str(ROOT))

    script_map = {
        "triage": "loop_triage.py",
        "select": "loop_select.py",
        "plan": "loop_plan.py",
        "verify": "loop_verify.py",
        "ops": "loop_ops_run.py",
    }
    script = ROOT / "scripts" / script_map[args.loop_cmd]
    cmd = [py, str(script)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.feature and args.loop_cmd in ("select", "plan", "verify"):
        cmd.extend(["--feature", args.feature])
    if args.loop_cmd == "plan" and not args.feature:
        raise SystemExit("loop plan requires --feature FEAT-xxx")
    if args.loop_cmd == "verify" and not args.feature:
        raise SystemExit("loop verify requires --feature FEAT-xxx")
    if args.loop_cmd == "ops":
        if args.date:
            cmd.extend(["--date", args.date])
        if args.refresh_context:
            cmd.append("--refresh-context")
    return subprocess.call(cmd, cwd=str(ROOT))


def cmd_config(args: argparse.Namespace) -> int:
    from core.config_schema import format_validation_report, validate_env_file
    from core.paths import ENV_FILE

    if args.config_cmd == "validate":
        path = Path(args.env) if args.env else ENV_FILE
        if not path.is_file():
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            print(f"Env file not found: {rel}")
            print("Copy .env.example → .env and add your API keys.")
            return 1
        report = validate_env_file(path)
        print(format_validation_report(report))
        if args.json:
            print(json.dumps(report.to_result().__dict__, indent=2))
        return 0 if report.ok else 1

    raise SystemExit(f"Unknown config command: {args.config_cmd}")


def cmd_lab(args: argparse.Namespace) -> int:
    port = int(args.port)
    if not args.no_dashboard:
        _start_dashboard_background(port)

    if args.mode == "sector":
        if not args.sector:
            raise SystemExit("lab sector requires --sector")
        rc = cmd_sector(args)
    else:
        rc = cmd_unified(args)

    if rc == 0 and not args.no_dashboard:
        print(f"\nOpen results:")
        print(f"  http://localhost:{port}/research/phoenix")
        print(f"  http://localhost:{port}/research/runs")
        print(f"  http://localhost:{port}/research/signals  (after: ./bin/mts export)")
    return rc


def _default_yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _resolve_enrich_max(args: argparse.Namespace) -> int:
    if getattr(args, "enrich_max", None) is not None:
        return int(args.enrich_max)
    return 10 if getattr(args, "full_agents", False) else 30


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mts",
        description="MyTradingSpace control plane — dashboard, backtests, analyze.",
    )
    p.add_argument(
        "--date",
        dest="global_date",
        metavar="YYYY-MM-DD",
        help="Default signal date for subcommands that accept --date",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pd = sub.add_parser("dashboard", help="Start Next.js backtest dashboard")
    pd.add_argument("--port", type=int, default=3055)
    pd.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="Start in background (for lab / scripts)",
    )
    pd.set_defaults(func=cmd_dashboard)

    ps = sub.add_parser("stop", help="Stop background dashboard")
    ps.add_argument("--port", type=int, default=3055)
    ps.set_defaults(func=cmd_stop)

    pa = sub.add_parser("analyze", help="Single-ticker or BUY/WATCH watchlist analyze (JSON)")
    pa.add_argument("--ticker", default=None, help="Required unless --watchlist")
    pa.add_argument("--watchlist", action="store_true", help="Deep-analyze all BUY/WATCH from master_pilot")
    pa.add_argument(
        "--trade-focus",
        action="store_true",
        help="Watchlist: BUY + WATCH with Phoenix score > 60 only",
    )
    pa.add_argument("--max-tickers", type=int, default=None, help="Cap watchlist batch size")
    pa.add_argument("--force", action="store_true", help="Re-analyze cached tickers (watchlist)")
    pa.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pa.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "phoenix", "fundamental", "full"],
    )
    pa.add_argument("--fund-data-source", default="yfinance", choices=["yfinance", "fmp"])
    pa.add_argument(
        "--export-breakdown",
        action="store_true",
        help="Write agent_breakdown markdown (full fusion; default under data/output/research/)",
    )
    pa.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Override markdown path (implies --export-breakdown)",
    )
    pa.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write analyze JSON (default auto-save for full fusion or --export-breakdown)",
    )
    pa.add_argument(
        "--refresh-context",
        action="store_true",
        help="Re-run macro, market_summary, geopolitics session cache (full fusion)",
    )
    pa.add_argument(
        "--strategy-profile",
        default="none",
        choices=["none", "minervini", "moglen", "breitstein", "mcintosh", "blend", "all"],
        help="Attach trader strategy layers (Minervini, Moglen, Breitstein, McIntosh)",
    )
    pa.set_defaults(func=cmd_analyze)

    pstr = sub.add_parser("strategy", help="Trader strategy layers only (JSON)")
    pstr.add_argument("--ticker", required=True)
    pstr.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pstr.add_argument(
        "--profile",
        default="blend",
        choices=["minervini", "moglen", "breitstein", "mcintosh", "blend", "all"],
    )
    pstr.set_defaults(func=cmd_strategy)

    pport = sub.add_parser("portfolio", help="Portfolio intelligence — backtest & allocate")
    pport_sub = pport.add_subparsers(dest="portfolio_cmd", required=True)

    pbt = pport_sub.add_parser("backtest", help="Momentum portfolio backtest (CAGR, drawdown, trade history)")
    pbt.add_argument("--start", required=True, metavar="YYYY-MM-DD")
    pbt.add_argument("--end", default=None, metavar="YYYY-MM-DD")
    pbt.add_argument("--budget", type=float, default=200_000, help="Initial capital (default 200000)")
    pbt.add_argument(
        "--universe",
        default="top10",
        choices=["top10", "full"],
        help="Halal universe scope (top10 = fast pilot)",
    )
    pbt.add_argument("--num-stocks", type=int, default=20, help="Portfolio size (default 20)")
    pbt.add_argument(
        "--enrich-agents",
        action="store_true",
        help="Enrich top names with Phoenix+strategy scores (slower, live APIs)",
    )
    pbt.add_argument(
        "--full-agents",
        action="store_true",
        help="Full orchestrator on top momentum names (default: 10 parallel enrich, ~3-5 min)",
    )
    pbt.add_argument(
        "--enrich-max",
        type=int,
        default=None,
        metavar="N",
        help="Max tickers for agent enrich (default: 10 with --full-agents, else 30)",
    )
    pbt.add_argument(
        "--enrich-workers",
        type=int,
        default=8,
        metavar="N",
        help="Parallel enrich workers (default 8)",
    )
    pbt.add_argument(
        "--strategy-profile",
        default="blend",
        choices=["minervini", "moglen", "breitstein", "mcintosh", "blend", "all"],
    )
    pbt.add_argument("--no-write", action="store_true", help="Skip writing CSV/JSON outputs")
    pbt.set_defaults(func=cmd_portfolio)

    pall = pport_sub.add_parser("allocate", help="Advisory portfolio book for a date")
    pall.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pall.add_argument("--budget", type=float, default=200_000)
    pall.add_argument("--universe", default="top10", choices=["top10", "full"])
    pall.add_argument("--num-stocks", type=int, default=20)
    pall.add_argument("--no-enrich", action="store_true", help="Momentum-only (skip agent enrich)")
    pall.add_argument(
        "--full-agents",
        action="store_true",
        help="Full orchestrator: Phoenix+FA+macro+news+insider+sentiment+geo+strategies. "
        "Fast default: 10 parallel enrich, ~3-5 min",
    )
    pall.add_argument(
        "--enrich-max",
        type=int,
        default=None,
        metavar="N",
        help="Max tickers for agent enrich (default: 10 with --full-agents, else 30). "
        "Portfolio may still hold 20 names; only top N get full agent scores blended in.",
    )
    pall.add_argument(
        "--enrich-workers",
        type=int,
        default=8,
        metavar="N",
        help="Parallel enrich workers (default 8)",
    )
    pall.add_argument(
        "--strategy-profile",
        default="blend",
        choices=["minervini", "moglen", "breitstein", "mcintosh", "blend", "all"],
    )
    pall.set_defaults(func=cmd_portfolio)

    pbd = sub.add_parser("export-breakdown", help="Export agent_breakdown from saved analyze JSON")
    pbd.add_argument(
        "--from-json",
        type=Path,
        required=True,
        help="Analyze JSON with agent_breakdown (from --fusion full)",
    )
    pbd.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown path (default data/output/research/<date>/<TICKER>_breakdown.md)",
    )
    pbd.set_defaults(func=cmd_export_breakdown)

    pc = sub.add_parser("sector", help="Single-sector master pilot")
    pc.add_argument("--sector", required=True)
    pc.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pc.add_argument("--eval-days", type=int, default=15)
    pc.set_defaults(func=cmd_sector)

    pu = sub.add_parser("unified", help="All-sector unified master pilot")
    pu.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pu.add_argument("--eval-days", type=int, default=15)
    pu.add_argument("--sector-jobs", type=int, default=11)
    pu.add_argument("--workers", type=int, default=8)
    pu.add_argument("--period-workers", type=int, default=2)
    pu.set_defaults(func=cmd_unified)

    pday = sub.add_parser("daily", help="Daily pipeline (unified + BUY excel + notify)")
    pday.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pday.add_argument("--eval-days", type=int, default=15)
    pday.add_argument("--no-export-buy", action="store_true")
    pday.add_argument("--no-telegram", action="store_true")
    pday.set_defaults(func=cmd_daily)

    pe = sub.add_parser("export", help="Reconcile Phoenix BUY/WATCH → Excel + JSON")
    pe.add_argument("--from", dest="date_from", default=None, metavar="YYYY-MM-DD")
    pe.add_argument("--to", dest="date_to", default=None, metavar="YYYY-MM-DD")
    pe.add_argument(
        "--lookback-days",
        type=int,
        default=14,
        help="When --from omitted, start this many days before --to (default 14)",
    )
    pe.add_argument("--signals", default="BUY,WATCH", help="Comma-separated, e.g. BUY,WATCH")
    pe.add_argument("--no-archive", action="store_true", help="Only scan data/output/trading_runs")
    pe.add_argument("--json-only", action="store_true", help="Skip Excel; refresh JSON only")
    pe.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "output" / "trading_runs" / "phoenix_signals_reconciled.xlsx",
    )
    pe.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="JSON path (default data/output/trading_runs/phoenix_signals_reconciled.json)",
    )
    pe.set_defaults(func=cmd_export)

    pl = sub.add_parser("lab", help="Backtest + dashboard together")
    pl.add_argument("mode", choices=["sector", "unified"])
    pl.add_argument("--sector", default=None, help="Required for lab sector")
    pl.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pl.add_argument("--eval-days", type=int, default=15)
    pl.add_argument("--sector-jobs", type=int, default=11)
    pl.add_argument("--workers", type=int, default=8)
    pl.add_argument("--period-workers", type=int, default=2)
    pl.add_argument("--port", type=int, default=3055)
    pl.add_argument("--no-dashboard", action="store_true", help="Run backtest only")
    pl.set_defaults(func=cmd_lab)

    pag = sub.add_parser("agent", help="Run a single registered agent (standalone JSON)")
    pag.add_argument(
        "agent_id",
        choices=["macro", "market_summary", "phoenix", "fundamental", "news", "insider", "sentiment", "geopolitics"],
        help="Registered agent id",
    )
    pag.add_argument("--ticker", default="", help="Ticker (required for phoenix/fundamental)")
    pag.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pag.add_argument("--envelope-only", action="store_true", help="Print envelope JSON only")
    pag.set_defaults(func=cmd_agent)

    pctx = sub.add_parser("context", help="Run session agents (macro + market_summary) → JSON cache")
    pctx.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pctx.set_defaults(func=cmd_context)

    ploop = sub.add_parser("loop", help="Loop engineering — triage, plan, verify, ops")
    ploop_sub = ploop.add_subparsers(dest="loop_cmd", required=True)
    for name, help_text in (
        ("triage", "Rank backlog → .loop/state/queue.json"),
        ("select", "Pick top feature from queue"),
        ("plan", "Write implementation plan (requires --feature)"),
        ("verify", "Run pytest gate (requires --feature)"),
        ("ops", "Research ops health check"),
        ("cycle", "Run triage → select → plan → worktree → verify"),
    ):
        sub_cmd = ploop_sub.add_parser(name, help=help_text)
        sub_cmd.add_argument("--feature", default=None, help="FEAT-xxx")
        sub_cmd.add_argument("--date", default=None, metavar="YYYY-MM-DD", help="For loop ops")
        sub_cmd.add_argument("--dry-run", action="store_true")
        sub_cmd.add_argument("--refresh-context", action="store_true", help="Run mts context before ops")
        sub_cmd.set_defaults(func=cmd_loop)

    pcfg = sub.add_parser("config", help="Validate .env against platform schema")
    pcfg_sub = pcfg.add_subparsers(dest="config_cmd", required=True)
    pval = pcfg_sub.add_parser("validate", help="Validate data-source and LLM env flags")
    pval.add_argument("--env", default=None, help="Path to .env (default: project .env)")
    pval.add_argument("--json", action="store_true", help="Also print JSON result")
    pval.set_defaults(func=cmd_config)

    return p


def _apply_default_dates(args: argparse.Namespace) -> None:
    if getattr(args, "command", None) == "loop" and getattr(args, "loop_cmd", None) == "ops":
        if getattr(args, "date", None) is None:
            args.date = getattr(args, "global_date", None) or _default_yesterday()
        return
    if not hasattr(args, "date"):
        return
    if args.date is not None:
        return
    if getattr(args, "command", None) == "daily":
        args.date = date.today().isoformat()
    else:
        args.date = getattr(args, "global_date", None) or _default_yesterday()


def _validate_agent_args(args: argparse.Namespace) -> None:
    if getattr(args, "command", None) != "agent":
        return
    agent_id = args.agent_id.strip().lower()
    ticker_agents = {"phoenix", "fundamental", "news", "insider", "sentiment"}
    if agent_id in ticker_agents and not (args.ticker or "").strip():
        raise SystemExit(f"agent {agent_id} requires --ticker")


def main(argv: Optional[List[str]] = None) -> int:
    _load_env()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_default_dates(args)
    _validate_agent_args(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
