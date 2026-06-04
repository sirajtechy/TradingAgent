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
        base.extend(
            [
                "--ticker",
                args.ticker,
                "--date",
                args.date,
                "--fusion",
                args.fusion,
                "--fund-data-source",
                args.fund_data_source,
            ]
        )
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


def cmd_analyze(args: argparse.Namespace) -> int:
    return subprocess.call(_pipeline_argv("analyze", args), cwd=str(ROOT))


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

    pa = sub.add_parser("analyze", help="Single-ticker analyze (JSON)")
    pa.add_argument("--ticker", required=True)
    pa.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    pa.add_argument(
        "--fusion",
        default="phoenix-fa",
        choices=["phoenix-fa", "phoenix", "fundamental"],
    )
    pa.add_argument("--fund-data-source", default="yfinance", choices=["yfinance", "fmp"])
    pa.set_defaults(func=cmd_analyze)

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

    return p


def _apply_default_dates(args: argparse.Namespace) -> None:
    if not hasattr(args, "date"):
        return
    if args.date is not None:
        return
    if getattr(args, "command", None) == "daily":
        args.date = date.today().isoformat()
    else:
        args.date = getattr(args, "global_date", None) or _default_yesterday()


def main(argv: Optional[List[str]] = None) -> int:
    _load_env()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_default_dates(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
