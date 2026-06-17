#!/usr/bin/env python3
"""Update loop state — journal entries and roadmap feature status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import (  # noqa: E402
    append_journal,
    load_roadmap,
    save_roadmap,
    utc_now_iso,
    FEATURE_JOURNAL,
    OPS_JOURNAL,
)

try:
    import yaml
except ImportError:
    yaml = None


def update_feature_status(feature_id: str, status: str, *, dry_run: bool = False) -> dict:
    data = load_roadmap()
    updated = False
    for feat in data.get("features") or []:
        if feat.get("id") == feature_id:
            feat["status"] = status
            updated = True
            break
    if not updated:
        return {"ok": False, "error": f"Feature {feature_id} not in roadmap"}

    if dry_run:
        return {"ok": True, "feature_id": feature_id, "status": status, "dry_run": True}

    if yaml is None:
        return {"ok": False, "error": "PyYAML required to save roadmap"}

    save_roadmap(data)
    append_journal(FEATURE_JOURNAL, f"Roadmap status `{feature_id}` → `{status}`.")
    return {"ok": True, "feature_id": feature_id, "status": status}


def append_ops_entry(entry: str, *, dry_run: bool = False) -> dict:
    if dry_run:
        return {"ok": True, "dry_run": True, "entry": entry}
    append_journal(OPS_JOURNAL, entry)
    return {"ok": True, "appended": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop update state")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("feature-status", help="Update roadmap feature status")
    p_status.add_argument("--feature", required=True)
    p_status.add_argument("--status", required=True, choices=["queued", "in_progress", "done", "blocked", "deferred"])
    p_status.add_argument("--dry-run", action="store_true")

    p_ops = sub.add_parser("ops-journal", help="Append ops journal entry")
    p_ops.add_argument("--message", required=True)
    p_ops.add_argument("--dry-run", action="store_true")

    p_note = sub.add_parser("journal", help="Append feature journal note")
    p_note.add_argument("--message", required=True)
    p_note.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "feature-status":
        result = update_feature_status(args.feature, args.status, dry_run=args.dry_run)
    elif args.command == "ops-journal":
        result = append_ops_entry(args.message, dry_run=args.dry_run)
    else:
        if args.dry_run:
            result = {"ok": True, "dry_run": True, "message": args.message}
        else:
            append_journal(FEATURE_JOURNAL, args.message)
            result = {"ok": True}

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
