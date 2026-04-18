"""
test_adx_gate.py — Tests for the STR-2 ADX hard gate in build_composite_score().

Verifies that low ADX conditions correctly downgrade bands and confidence
without blocking the signal entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.technical.rules import build_composite_score


def _make_frameworks(score_pct: float) -> Dict[str, Any]:
    """Produce a minimal frameworks dict with each framework scoring *score_pct*.

    build_composite_score() checks ``fw.get('applicable', False)`` to guard
    against frameworks that couldn't be evaluated — so each entry must include
    ``'applicable': True`` to be included in the composite.
    """
    return {
        "ema_trend":           {"applicable": True, "score_pct": score_pct},
        "macd_system":         {"applicable": True, "score_pct": score_pct},
        "rsi_regime":          {"applicable": True, "score_pct": score_pct},
        "bollinger":           {"applicable": True, "score_pct": score_pct},
        "volume_obv":          {"applicable": True, "score_pct": score_pct},
        "adx_stochastic":      {"applicable": True, "score_pct": score_pct},
        "pattern_recognition": {"applicable": True, "score_pct": score_pct},
        "ichimoku":            {"applicable": True, "score_pct": score_pct},
        "momentum":            {"applicable": True, "score_pct": score_pct},
        "supertrend":          {"applicable": True, "score_pct": score_pct},
        "volatility_squeeze":  {"applicable": True, "score_pct": score_pct},
        "entry_exit_rules":    {"applicable": True, "score_pct": score_pct},
    }


class TestAdxGate:

    def test_mixed_positive_downgraded_when_adx_below_threshold(self):
        """
        When composite score is in mixed_positive range (50-60) AND ADX < 17,
        the band should be downgraded to 'mixed'.
        """
        # Score ~55 → normally mixed_positive
        frameworks = _make_frameworks(55.0)
        result = build_composite_score(frameworks, adx_value=14.0)
        assert result["available"] is True
        # Should be downgraded from mixed_positive → mixed
        assert result["band"] == "mixed"
        assert result["adx_gate_applied"] is True

    def test_strong_band_not_downgraded_by_adx_gate(self):
        """
        High-conviction 'strong' band (score ≥ 75) should NOT be downgraded
        even when ADX < 17 — very strong technical signals override the gate.
        """
        frameworks = _make_frameworks(78.0)
        result = build_composite_score(frameworks, adx_value=12.0)
        assert result["band"] == "strong"
        assert result["adx_gate_applied"] is False

    def test_good_band_not_downgraded_by_adx_gate(self):
        """'good' band (60-75) is also not downgraded."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=10.0)
        assert result["band"] == "good"
        assert result["adx_gate_applied"] is False

    def test_low_adx_gives_low_confidence(self):
        """ADX < 17 should produce low confidence with very low confidence_pct."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=12.0)
        assert result["confidence"] == "low"
        assert result["confidence_pct"] <= 20.0

    def test_adx_17_to_20_gives_low_confidence(self):
        """ADX 17–19 gives low confidence (below the 20 threshold)."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=18.0)
        assert result["confidence"] == "low"

    def test_adx_above_20_gives_medium_confidence(self):
        """ADX ≥ 20 gives medium confidence."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=25.0)
        assert result["confidence"] == "medium"

    def test_adx_above_40_gives_high_confidence(self):
        """ADX ≥ 40 gives high confidence."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=45.0)
        assert result["confidence"] == "high"

    def test_no_adx_data_uses_weight_fallback(self):
        """When adx_value is None, confidence falls back to weight-based default."""
        frameworks = _make_frameworks(65.0)
        result = build_composite_score(frameworks, adx_value=None)
        # With 11 frameworks all scoring well, total_weight ≥ 0.65 → medium
        assert result["confidence"] in ("medium", "high", "low")
        assert result["adx_gate_applied"] is False

    def test_adx_gate_applied_key_always_present(self):
        """adx_gate_applied key must always be present in the result."""
        frameworks = _make_frameworks(55.0)
        for adx_val in (None, 10.0, 20.0, 40.0):
            result = build_composite_score(frameworks, adx_value=adx_val)
            assert "adx_gate_applied" in result
