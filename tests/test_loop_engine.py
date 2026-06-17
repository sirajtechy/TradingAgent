"""Tests for loop engineering scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from loop_common import load_roadmap, score_feature  # noqa: E402


@pytest.fixture
def roadmap():
    return load_roadmap()


def test_roadmap_has_features(roadmap):
    assert len(roadmap.get("features") or []) >= 3


def test_feat_001_done_in_roadmap(roadmap):
    feat = next(f for f in roadmap["features"] if f["id"] == "FEAT-001")
    assert feat.get("status") == "done"
    assert score_feature(feat) == 0


def test_feat_002_done_in_roadmap(roadmap):
    feat = next(f for f in roadmap["features"] if f["id"] == "FEAT-002")
    assert feat.get("status") == "done"
    assert score_feature(feat) == 0


def test_feat_003_done_in_roadmap(roadmap):
    feat = next(f for f in roadmap["features"] if f["id"] == "FEAT-003")
    assert feat.get("status") == "done"
    assert score_feature(feat) == 0


def test_feat_004_not_auto_eligible(roadmap):
    feat = next(f for f in roadmap["features"] if f["id"] == "FEAT-004")
    assert feat.get("auto_eligible") is False
    assert score_feature(feat) == 0


def test_loop_triage_dry_run(roadmap):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "loop_triage.py"), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "items" in data
    eligible = [f for f in roadmap["features"] if score_feature(f) > 0]
    assert len(data["items"]) == len(eligible)


def test_loop_select_after_triage(roadmap):
    subprocess.run([sys.executable, str(SCRIPTS / "loop_triage.py")], cwd=ROOT, check=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "loop_select.py"), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    eligible = [f for f in roadmap["features"] if score_feature(f) > 0]
    if not eligible:
        assert proc.returncode == 1
        assert data.get("ok") is False
        return
    assert proc.returncode == 0
    assert data.get("ok") is True
    assert data.get("selected", {}).get("id", "").startswith("FEAT-")


def test_loop_plan_dry_run():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "loop_plan.py"), "--feature", "FEAT-001", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data.get("ok") is True


def test_loop_verify_dry_run():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "loop_verify.py"), "--feature", "FEAT-001", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


def test_loop_ops_dry_run():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "loop_ops_run.py"), "--date", "2026-06-06", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data.get("as_of_date") == "2026-06-06"


def test_loop_policies_exist():
    for name in ("feature-selection.md", "risk-guardrails.md", "done-criteria.md"):
        assert (ROOT / ".loop" / "policies" / name).is_file()


def test_loop_skills_exist():
    skills = ROOT / ".loop" / "skills"
    assert (skills / "feature-planning" / "SKILL.md").is_file()
    assert (skills / "mts-cli-ops" / "SKILL.md").is_file()
