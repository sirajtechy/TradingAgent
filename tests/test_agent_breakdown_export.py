"""Tests for agent_breakdown markdown export (FEAT-002)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.orchestrator.agent_breakdown import (
    ALL_AGENT_IDS,
    default_breakdown_markdown_path,
    export_agent_breakdown_markdown,
    render_agent_breakdown_markdown,
    write_agent_breakdown_markdown,
)

FIXTURE = Path(__file__).parent / "fixtures" / "agent_breakdown_sample.json"


@pytest.fixture
def sample_doc() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_default_breakdown_markdown_path():
    path = default_breakdown_markdown_path("nvda", "2026-06-06")
    assert path.name == "NVDA_breakdown.md"
    assert "2026-06-06" in str(path)
    assert path.parent.name == "2026-06-06"


def test_render_includes_all_agents_and_human_note(sample_doc):
    md = render_agent_breakdown_markdown(
        sample_doc["agent_breakdown"],
        fusion=sample_doc["fusion"],
    )
    assert "Human decision mode" in md
    assert sample_doc["agent_breakdown"]["note"] in md
    assert "7/8 agents available" in md or "7/9 agents available" in md
    for agent_id in ALL_AGENT_IDS:
        title = agent_id.replace("_", " ").title()
        assert f"## {title}" in md
    assert "**Status:** ok" in md
    assert "**Signal:** bullish (75.0)" in md
    assert "Stage 2 base breakout" in md
    assert "**Error:** API timeout" in md
    assert "Fusion (reference only)" in md
    assert "**Advisory:** BUY" in md


def test_write_and_export_from_fixture(tmp_path, sample_doc):
    out = tmp_path / "NVDA_breakdown.md"
    write_agent_breakdown_markdown(sample_doc["agent_breakdown"], out, fusion=sample_doc["fusion"])
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "NVDA @ 2026-06-06" in text

    exported = export_agent_breakdown_markdown(sample_doc, tmp_path / "re_export.md")
    assert exported.read_text(encoding="utf-8") == text


def test_export_missing_breakdown_raises():
    with pytest.raises(ValueError, match="missing agent_breakdown"):
        export_agent_breakdown_markdown({"ok": True, "fusion_mode": "phoenix-fa"})


def test_cli_export_breakdown_from_fixture(tmp_path, sample_doc):
    import subprocess
    import sys

    root = Path(__file__).resolve().parent.parent
    src = tmp_path / "analyze.json"
    src.write_text(json.dumps(sample_doc), encoding="utf-8")
    out = tmp_path / "out.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "cli" / "__main__.py"),
            "export-breakdown",
            "--from-json",
            str(src),
            "--output",
            str(out),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    assert "Human decision mode" in out.read_text(encoding="utf-8")
