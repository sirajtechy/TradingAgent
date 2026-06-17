#!/usr/bin/env python3
"""Research ops loop — session health check and artifact paths (read-only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import append_journal, utc_now_iso, OPS_JOURNAL  # noqa: E402

CONTEXT_DIR = ROOT / "data" / "output" / "context"
RESEARCH_DIR = ROOT / "data" / "output" / "research"
SESSION_AGENTS = ("macro", "market_summary", "geopolitics")
MTS = ROOT / "bin" / "mts"


def _resolve_date(as_of: str | None) -> str:
    if as_of:
        return as_of
    return (date.today() - timedelta(days=1)).isoformat()


def _check_context_cache(as_of: str) -> dict:
    path = CONTEXT_DIR / f"context_{as_of}.json"
    if not path.is_file():
        return {"ok": False, "path": str(path.relative_to(ROOT)), "agents_ok": 0, "agents_total": 3}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "path": str(path.relative_to(ROOT)), "error": "invalid json"}

    agents = data.get("agents") or {}
    ok_count = 0
    details = {}
    for aid in SESSION_AGENTS:
        bundle = agents.get(aid) or {}
        native = bundle.get("native")
        err = bundle.get("error")
        status = "ok" if native else ("error" if err else "missing")
        if status == "ok":
            ok_count += 1
        details[aid] = status

    return {
        "ok": ok_count == len(SESSION_AGENTS),
        "path": str(path.relative_to(ROOT)),
        "agents_ok": ok_count,
        "agents_total": len(SESSION_AGENTS),
        "details": details,
    }


def run_ops(*, as_of: str, refresh_context: bool = False, dry_run: bool = False) -> dict:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = RESEARCH_DIR / as_of
    result = {
        "as_of_date": as_of,
        "generated_at": utc_now_iso(),
        "dry_run": dry_run,
    }

    if refresh_context and not dry_run and MTS.is_file():
        proc = subprocess.run(
            [str(MTS), "context", "--date", as_of],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        result["context_run"] = {"returncode": proc.returncode, "ok": proc.returncode == 0}

    cache = _check_context_cache(as_of)
    result["context_cache"] = cache

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "as_of_date": as_of,
            "context_cache": cache,
            "research_output_dir": str(out_dir.relative_to(ROOT)),
            "note": "Run ./bin/mts analyze --fusion full --ticker X --date for per-ticker JSON",
        }
        (out_dir / "ops_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    agents_line = f"{cache.get('agents_ok', 0)}/{cache.get('agents_total', 3)} session agents ok"
    entry = (
        f"Ops run `{as_of}` — context cache {cache.get('path')}: {agents_line}. "
        f"Research dir: `data/output/research/{as_of}/`."
    )

    if not dry_run:
        append_journal(OPS_JOURNAL, entry)

    result["summary"] = entry
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Research ops loop — health + artifacts")
    parser.add_argument("--date", dest="as_of", default=None, help="YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--refresh-context", action="store_true", help="Run ./bin/mts context first")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    as_of = _resolve_date(args.as_of)
    result = run_ops(as_of=as_of, refresh_context=args.refresh_context, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("context_cache", {}).get("ok", False) or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
