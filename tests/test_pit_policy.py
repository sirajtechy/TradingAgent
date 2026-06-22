"""Tests for PIT policy helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

from core.evaluation.pit_policy import agent_pit_status, pit_manifest_for_date


def test_technical_always_allowed() -> None:
    st = agent_pit_status("technical", "2020-01-01")
    assert st["allowed"] is True


def test_macro_requires_fred_key() -> None:
    with patch.dict(os.environ, {}, clear=True):
        st = agent_pit_status("macro", "2024-06-01")
        assert st["allowed"] is False
    with patch.dict(os.environ, {"FRED_API_KEY": "test"}):
        st = agent_pit_status("macro", "2024-06-01")
        assert st["allowed"] is True


def test_pit_manifest_includes_agents() -> None:
    manifest = pit_manifest_for_date("2025-01-15")
    assert manifest["as_of_date"] == "2025-01-15"
    assert "macro" in manifest["agents"]
    assert "fusion_full" in manifest["agents"]
