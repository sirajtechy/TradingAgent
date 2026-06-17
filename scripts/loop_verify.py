#!/usr/bin/env python3
"""Verify feature readiness — run pytest and write artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from loop_common import (  # noqa: E402
    append_journal,
    get_feature_by_id,
    run_pytest,
    utc_now_iso,
    FEATURE_JOURNAL,
    LOOP_DIR,
)


def run_verify(feature_id: str, *, dry_run: bool = False, skip_tests: bool = False) -> dict:
    feat = get_feature_by_id(feature_id)
    if not feat:
        return {"ok": False, "error": f"Unknown feature {feature_id}"}

    artifact_dir = LOOP_DIR / "state" / "verify"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{feature_id}.json"

    if dry_run:
        return {
            "ok": True,
            "feature_id": feature_id,
            "dry_run": True,
            "would_run": "pytest tests/ -q",
        }

    checks = {"pytest": {"ok": True, "skipped": skip_tests}}

    if not skip_tests:
        proc = run_pytest(ROOT)
        checks["pytest"] = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
        }

    ok = all(c.get("ok") for c in checks.values())
    artifact = {
        "feature_id": feature_id,
        "verified_at": utc_now_iso(),
        "ok": ok,
        "checks": checks,
    }
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    status = "pass" if ok else "fail"
    append_journal(
        FEATURE_JOURNAL,
        f"Verify {status} for `{feature_id}` — artifact `{artifact_path.relative_to(ROOT)}`.",
    )

    return {"ok": ok, "artifact": str(artifact_path.relative_to(ROOT)), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Loop verify — pytest + artifact")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    result = run_verify(
        args.feature,
        dry_run=args.dry_run,
        skip_tests=args.skip_tests,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
