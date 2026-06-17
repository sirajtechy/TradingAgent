"""Tests for --refresh-context session cache (FEAT-003)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agents.orchestrator.pipeline_full import (
    SESSION_AGENT_IDS,
    load_or_run_session_context,
)
from pipelines.analyze import analyze_single

ROOT = Path(__file__).resolve().parent.parent


def _cached_agents(tag: str) -> dict:
    return {
        aid: {
            "native": {"cached": tag, "agent": aid},
            "envelope": {"signal": "neutral", "score": 50.0},
            "error": None,
        }
        for aid in SESSION_AGENT_IDS
    }


def test_load_or_run_session_context_uses_cache_without_refresh(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "agents.orchestrator.pipeline_full._CONTEXT_DIR",
        tmp_path,
    )
    cache_path = tmp_path / "context_2026-06-06.json"
    cache_path.write_text(
        json.dumps({"as_of_date": "2026-06-06", "agents": _cached_agents("old")}),
        encoding="utf-8",
    )

    calls: list[str] = []

    def fake_safe(agent_id: str, **kwargs):
        calls.append(agent_id)
        return {"fresh": True}, {"signal": "bullish", "score": 80.0}, None

    monkeypatch.setattr("agents.orchestrator.pipeline_full._safe_analyze", fake_safe)

    agents = load_or_run_session_context("2026-06-06", refresh=False)
    assert calls == []
    assert agents["macro"]["native"]["cached"] == "old"


def test_load_or_run_session_context_refresh_reruns_session_agents(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "agents.orchestrator.pipeline_full._CONTEXT_DIR",
        tmp_path,
    )
    cache_path = tmp_path / "context_2026-06-06.json"
    cache_path.write_text(
        json.dumps({"as_of_date": "2026-06-06", "agents": _cached_agents("stale")}),
        encoding="utf-8",
    )

    calls: list[str] = []

    def fake_safe(agent_id: str, **kwargs):
        calls.append(agent_id)
        return {"fresh": True, "agent": agent_id}, {"signal": "bullish", "score": 80.0}, None

    monkeypatch.setattr("agents.orchestrator.pipeline_full._safe_analyze", fake_safe)

    agents = load_or_run_session_context("2026-06-06", refresh=True)
    assert set(calls) == set(SESSION_AGENT_IDS)
    assert agents["macro"]["native"]["fresh"] is True
    updated = json.loads(cache_path.read_text(encoding="utf-8"))
    assert updated["agents"]["macro"]["native"]["fresh"] is True


def test_analyze_single_passes_refresh_context(monkeypatch):
    captured: dict = {}

    def fake_run_full(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "fusion_mode": "full", "context_refreshed": True}

    monkeypatch.setattr(
        "agents.orchestrator.pipeline_full.run_full_analysis",
        fake_run_full,
    )

    doc = analyze_single(
        ticker="NVDA",
        as_of_date="2026-06-06",
        fusion="full",
        refresh_context=True,
    )
    assert captured.get("refresh_context") is True
    assert doc.get("context_refreshed") is True


def test_cli_analyze_accepts_refresh_context_flag():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "cli" / "__main__.py"), "analyze", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--refresh-context" in proc.stdout
