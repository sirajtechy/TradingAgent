"""Tests for backtest signal profiles."""

from __future__ import annotations

from agents.technical.backtest_signal import derive_backtest_signal
from agents.technical.fusion import build_technical_fusion
from tests.test_technical_agent import _layer, _phoenix


def _fusion_for(phoenix: dict) -> object:
    layers = {sid: _layer(sid) for sid in ("minervini", "moglen", "breitstein", "mcintosh")}
    return build_technical_fusion(phoenix, layers)


def test_phoenix_recall_watch_is_bullish():
    px = _phoenix(signal="WATCH", hard_pass=True)
    assert derive_backtest_signal(px, _fusion_for(px), profile="phoenix_recall") == "bullish"


def test_phoenix_recall_avoid_is_neutral_not_bearish():
    px = _phoenix(signal="AVOID", hard_pass=False)
    assert derive_backtest_signal(px, _fusion_for(px), profile="phoenix_recall") == "neutral"


def test_enrichment_strict_needs_pass():
    px = _phoenix(signal="WATCH", hard_pass=True)
    fusion = build_technical_fusion(
        px,
        {
            "minervini": _layer("minervini", entry_trigger=False),
            "moglen": _layer("moglen", entry_trigger=False, signal="bearish"),
            "breitstein": _layer("breitstein", entry_trigger=False, signal="bearish"),
            "mcintosh": _layer("mcintosh", entry_trigger=False, signal="bearish"),
        },
    )
    assert derive_backtest_signal(px, fusion, profile="enrichment_strict") == "neutral"
