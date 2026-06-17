#!/usr/bin/env python3
"""Generate implementation plan for a feature from roadmap + template."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import (  # noqa: E402
    PLANS_DIR,
    append_journal,
    get_feature_by_id,
    load_queue,
    render_template,
    utc_now_iso,
    FEATURE_JOURNAL,
)


def run_plan(feature_id: str, *, dry_run: bool = False) -> dict:
    feat = get_feature_by_id(feature_id)
    if not feat:
        return {"ok": False, "error": f"Unknown feature {feature_id}"}

    criteria_lines = "\n".join(
        f"- {c}" for c in (feat.get("acceptance_criteria") or [])
    )
    plan_body = render_template(
        "implementation-plan.md",
        FEATURE_ID=feature_id,
        DATE=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        TITLE=str(feat.get("title") or feature_id),
    )
    # Inject acceptance criteria after section header
    plan_body = plan_body.replace(
        "<!-- from roadmap.yaml -->",
        criteria_lines or "- (none defined)",
    )

    plan_path = PLANS_DIR / f"{feature_id}.md"
    result = {
        "ok": True,
        "feature_id": feature_id,
        "plan_path": str(plan_path.relative_to(ROOT)),
        "title": feat.get("title"),
    }

    if dry_run:
        result["plan_preview"] = plan_body[:500]
        return result

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan_body, encoding="utf-8")
    append_journal(
        FEATURE_JOURNAL,
        f"Planner completed for `{feature_id}` → `{plan_path.relative_to(ROOT)}`.",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop plan — write implementation plan")
    parser.add_argument("--feature", required=True, help="Feature ID e.g. FEAT-001")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Default to selected feature from queue if --feature omitted in future
    result = run_plan(args.feature, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
