#!/usr/bin/env python3
"""Select top auto-eligible feature from queue and mark for build."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import append_journal, load_queue, save_queue, utc_now_iso, FEATURE_JOURNAL  # noqa: E402


def run_select(*, feature_id: str | None = None, dry_run: bool = False) -> dict:
    queue = load_queue()
    items = queue.get("items") or []

    if not items:
        return {"ok": False, "error": "Queue empty — run loop_triage.py first"}

    selected = None
    if feature_id:
        for item in items:
            if item.get("id") == feature_id:
                selected = item
                break
        if not selected:
            return {"ok": False, "error": f"Feature {feature_id} not in queue"}
    else:
        selected = items[0]

    queue["selected_feature_id"] = selected["id"]
    queue["selected_at"] = utc_now_iso()
    for item in items:
        if item.get("id") == selected["id"]:
            item["status"] = "selected"
        elif item.get("status") == "selected":
            item["status"] = "candidate"

    result = {"ok": True, "selected": selected}

    if dry_run:
        return result

    save_queue(queue)
    append_journal(
        FEATURE_JOURNAL,
        f"Selected `{selected['id']}` — {selected.get('title')} (score={selected.get('score')}).",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop select — pick feature to build")
    parser.add_argument("--feature", dest="feature_id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_select(feature_id=args.feature_id, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
