"""Unit tests for unified Technical Agent (Phase T1)."""

from __future__ import annotations

from unittest.mock import patch

from agents._registry import analyze_and_envelope
from agents.technical.envelope import envelope_from_unified_technical
from agents.technical.fusion import (
    build_technical_fusion,
    compute_resilience_score,
    derive_technical_signal,
)
from agents.technical.service import analyze_technical


def _phoenix(*, signal: str = "BUY", hard_pass: bool = True, score: float = 82.0) -> dict:
    return {
        "ticker": "TEST",
        "signal": signal,
        "score": score,
        "hard_filter_passed": hard_pass,
        "hard_filter_reason": None if hard_pass else "Price below 200-day SMA",
        "stage": {"stage": 2, "label": "Momentum"},
        "pattern": {"pattern_name": "VCP", "confirmed": True},
        "extension_guardrail": {"chase_risk": "low"},
    }


def _layer(
    sid: str,
    *,
    entry_trigger: bool = True,
    signal: str = "bullish",
    score: float = 70.0,
    regime_ok: bool = True,
) -> dict:
    subscores = {}
    if sid == "minervini":
        subscores = {"trend_template_pass_count": 8}
    elif sid == "moglen":
        subscores = {"rmv15": 12.0}
    elif sid == "mcintosh":
        subscores = {"fastest_horse_rank": 80.0}
    return {
        "strategy_id": sid,
        "signal": signal,
        "score": score,
        "entry_trigger": entry_trigger,
        "regime_ok": regime_ok,
        "subscores": subscores,
        "disqualifiers": [],
    }


def test_build_technical_fusion_passes_enrichment():
    layers = {
        "minervini": _layer("minervini"),
        "moglen": _layer("moglen"),
        "breitstein": _layer("breitstein"),
        "mcintosh": _layer("mcintosh"),
    }
    fusion = build_technical_fusion(_phoenix(), layers)
    assert fusion.pass_enrichment is True
    assert fusion.consensus_entry_triggers >= 2
    assert fusion.resilience_score > 0
    assert derive_technical_signal(_phoenix(), fusion) == "bullish"


def test_build_technical_fusion_blocks_on_hard_filter_fail():
    layers = {sid: _layer(sid) for sid in ("minervini", "moglen", "breitstein", "mcintosh")}
    fusion = build_technical_fusion(_phoenix(hard_pass=False, signal="AVOID"), layers)
    assert fusion.pass_enrichment is False
    assert derive_technical_signal(_phoenix(hard_pass=False, signal="AVOID"), fusion) == "bearish"


def test_build_technical_fusion_minervini_moglen_or_path():
    layers = {
        "minervini": _layer("minervini", entry_trigger=True),
        "moglen": _layer("moglen", entry_trigger=False),
        "breitstein": _layer("breitstein", entry_trigger=False),
        "mcintosh": _layer("mcintosh", entry_trigger=False),
    }
    fusion = build_technical_fusion(_phoenix(), layers)
    assert fusion.pass_enrichment is True


def test_build_technical_fusion_insufficient_consensus():
    layers = {
        "minervini": _layer("minervini", entry_trigger=False),
        "moglen": _layer("moglen", entry_trigger=False, regime_ok=False),
        "breitstein": _layer("breitstein", entry_trigger=False),
        "mcintosh": _layer("mcintosh", entry_trigger=False),
    }
    fusion = build_technical_fusion(_phoenix(), layers)
    assert fusion.pass_enrichment is False
    assert "Enrichment gate closed" in fusion.pass_reason


def test_resilience_score_chase_penalty():
    phoenix = _phoenix()
    phoenix["extension_guardrail"] = {"chase_risk": "elevated"}
    layers = {"minervini": _layer("minervini")}
    low = compute_resilience_score(phoenix, layers)
    phoenix["extension_guardrail"] = {"chase_risk": "low"}
    high = compute_resilience_score(phoenix, layers)
    assert high > low


def test_envelope_from_unified_technical():
    native = {
        "as_of_date": "2025-09-01",
        "signal": "bullish",
        "score": 76.0,
        "confidence": "high",
        "data_quality": "good",
        "warnings": [],
        "disqualifiers": [],
        "strategy_profile": "blend",
        "phoenix": _phoenix(),
        "strategy_layers": {"minervini": _layer("minervini")},
        "technical_fusion": {
            "pass_enrichment": True,
            "pass_reason": "Phoenix BUY + 4/4 entry triggers + blend bullish",
            "resilience_score": 74.0,
            "blend_signal": "bullish",
        },
    }
    env = envelope_from_unified_technical(native, as_of_date="2025-09-01")
    assert env["agent_id"] == "technical"
    assert env["signal"] == "bullish"
    assert env["extras"]["technical_fusion"]["pass_enrichment"] is True


@patch("agents.technical.service.phoenix_analyze")
@patch("agents.technical.service.analyze_strategies")
@patch("agents.technical.service._get_client")
def test_analyze_technical_orchestrates_layers(mock_client, mock_strategies, mock_phoenix):
    mock_phoenix.return_value = _phoenix()
    mock_strategies.return_value = {
        "layers": {sid: _layer(sid) for sid in ("minervini", "moglen", "breitstein", "mcintosh")},
        "warnings": [],
    }
    mock_client.return_value.build_snapshot.return_value = object()

    out = analyze_technical(ticker="nvda", as_of_date="2025-09-01", strategy_profile="blend")
    assert out["ok"] is True
    assert out["ticker"] == "NVDA"
    assert out["technical_fusion"]["pass_enrichment"] is True
    mock_phoenix.assert_called_once()
    mock_strategies.assert_called_once()
    call_kw = mock_strategies.call_args.kwargs
    px_kw = call_kw["phoenix_result"]
    # `maybe_upgrade_phoenix` annotates the dict with provenance keys before
    # forwarding to strategies. For a hard_pass=True BUY, the upgrade is a
    # no-op (entry_mode stays "standard") but the keys are now present.
    for k, v in mock_phoenix.return_value.items():
        assert px_kw[k] == v
    assert px_kw["phoenix_entry_mode"] == "standard"
    assert call_kw["fetch_market_data"] is False


@patch("agents._registry.analyze_technical")
def test_registry_technical_agent(mock_analyze):
    mock_analyze.return_value = {
        "as_of_date": "2025-09-01",
        "signal": "bullish",
        "score": 76.0,
        "confidence": "high",
        "data_quality": "good",
        "warnings": [],
        "disqualifiers": [],
        "strategy_profile": "blend",
        "phoenix": _phoenix(),
        "strategy_layers": {},
        "technical_fusion": {"pass_enrichment": True, "pass_reason": "ok"},
    }
    native, envelope = analyze_and_envelope(
        "technical",
        ticker="TEST",
        as_of_date="2025-09-01",
    )
    assert native["signal"] == "bullish"
    assert envelope["agent_id"] == "technical"
