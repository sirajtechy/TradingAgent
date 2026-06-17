#!/usr/bin/env python3
"""Discover and rank loop-eligible work; update queue.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import (  # noqa: E402
    append_journal,
    find_todos,
    git_recent_commits,
    load_queue,
    load_roadmap,
    save_queue,
    score_feature,
    utc_now_iso,
    FEATURE_JOURNAL,
)


def run_triage(*, dry_run: bool = False) -> dict:
    roadmap = load_roadmap()
    items = []

    for feat in roadmap.get("features") or []:
        sc = score_feature(feat)
        if sc <= 0:
            continue
        items.append({
            "id": feat.get("id"),
            "title": feat.get("title"),
            "score": sc,
            "status": "candidate",
            "auto_eligible": bool(feat.get("auto_eligible")),
            "risk_level": feat.get("risk_level"),
            "reason": f"roadmap priority={feat.get('priority')} risk={feat.get('risk_level')}",
        })

    items.sort(key=lambda x: x["score"], reverse=True)

    todos = find_todos(ROOT)
    signals = {
        "todo_count": len(todos),
        "todo_sample": todos[:5],
        "recent_commits": git_recent_commits(ROOT, 5),
    }

    queue = {
        "generated_at": utc_now_iso(),
        "selected_feature_id": None,
        "signals": signals,
        "items": items,
    }

    if dry_run:
        return queue

    save_queue(queue)
    summary = f"Triage complete: {len(items)} candidate(s). Top: {items[0]['id'] if items else 'none'}."
    append_journal(FEATURE_JOURNAL, summary)
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop triage — rank features and update queue")
    parser.add_argument("--dry-run", action="store_true", help="Print queue JSON without writing")
    args = parser.parse_args()

    result = run_triage(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
