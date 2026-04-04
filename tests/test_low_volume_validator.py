"""
test_low_volume_validator.py — Tests for the low-volume stock reliability module.

Uses synthetic price/volume data so no network calls are needed.
"""

import pytest

from agents.technical.low_volume_validator import (
    ADEQUATE_VOLUME_THRESHOLD,
    LOW_VOLUME_THRESHOLD,
    PENNY_STOCK_THRESHOLD,
    VERY_LOW_VOLUME_THRESHOLD,
    apply_reliability_adjustments,
    validate_stock_reliability,
)


# ====================================================================== #
# validate_stock_reliability                                               #
# ====================================================================== #

class TestValidateStockReliability:

    def test_reliable_stock(self):
        """High-cap stock with ample volume → reliable."""
        closes = [150.0] * 100
        volumes = [5_000_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "AAPL")
        assert result["reliability_grade"] == "reliable"
        assert result["confidence_adjustment"] == 0.0
        assert result["warnings"] == []

    def test_very_low_volume(self):
        """Average volume < 100K → unreliable or caution."""
        closes = [50.0] * 100
        volumes = [50_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "THINLY")
        assert result["reliability_grade"] in ("unreliable", "caution")
        assert result["confidence_adjustment"] < 0
        assert any("VERY LOW VOLUME" in w for w in result["warnings"])

    def test_low_volume(self):
        """Average volume 100K-500K → caution."""
        closes = [50.0] * 100
        volumes = [300_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "LOWVOL")
        assert result["confidence_adjustment"] < 0
        assert any("LOW VOLUME" in w for w in result["warnings"])

    def test_penny_stock(self):
        """Price < $5 → penny stock warning."""
        closes = [3.50] * 100
        volumes = [5_000_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "PENNY")
        assert result["confidence_adjustment"] < 0
        assert any("PENNY STOCK" in w for w in result["warnings"])
        assert "bollinger" in result.get("indicator_warnings", {}) or \
               "patterns" in result.get("indicator_warnings", {})

    def test_low_price(self):
        """Price $5-$10 → low price note."""
        closes = [7.0] * 100
        volumes = [5_000_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "LOWP")
        assert any("LOW PRICE" in w for w in result["warnings"])

    def test_empty_data(self):
        result = validate_stock_reliability([], [], "EMPTY")
        assert result["reliability_grade"] == "insufficient_data"
        assert result["confidence_adjustment"] == -0.5

    def test_indicator_warnings_for_low_volume(self):
        """Low volume stocks should get OBV, CMF, VWAP warnings."""
        closes = [50.0] * 100
        volumes = [50_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "THIN")
        iw = result.get("indicator_warnings", {})
        assert "obv" in iw
        assert "cmf" in iw
        assert "vwap" in iw

    def test_metrics_present(self):
        closes = [100.0] * 100
        volumes = [2_000_000.0] * 100
        result = validate_stock_reliability(closes, volumes, "TEST")
        metrics = result["metrics"]
        assert "current_price" in metrics
        assert "avg_volume_20d" in metrics
        assert "volume_class" in metrics
        assert "price_class" in metrics


# ====================================================================== #
# apply_reliability_adjustments                                            #
# ====================================================================== #

class TestApplyReliabilityAdjustments:

    def _make_evaluation(self, confidence="high"):
        return {
            "experimental_score": {
                "available": True,
                "score": 70.0,
                "band": "good",
                "confidence": confidence,
            },
            "warnings": ["Existing warning."],
        }

    def test_reliable_no_changes(self):
        evaluation = self._make_evaluation()
        reliability = {
            "reliability_grade": "reliable",
            "confidence_adjustment": 0.0,
            "warnings": [],
        }
        result = apply_reliability_adjustments(evaluation, reliability)
        assert result["experimental_score"]["confidence"] == "high"
        assert result["reliability"] == reliability

    def test_unreliable_downgrades_to_low(self):
        evaluation = self._make_evaluation(confidence="high")
        reliability = {
            "reliability_grade": "unreliable",
            "confidence_adjustment": -0.5,
            "warnings": ["VERY LOW VOLUME: test."],
        }
        result = apply_reliability_adjustments(evaluation, reliability)
        assert result["experimental_score"]["confidence"] == "low"
        assert "reliability_note" in result["experimental_score"]

    def test_caution_caps_at_medium(self):
        evaluation = self._make_evaluation(confidence="high")
        reliability = {
            "reliability_grade": "caution",
            "confidence_adjustment": -0.2,
            "warnings": ["LOW VOLUME: test."],
        }
        result = apply_reliability_adjustments(evaluation, reliability)
        assert result["experimental_score"]["confidence"] == "medium"

    def test_warnings_appended(self):
        evaluation = self._make_evaluation()
        reliability = {
            "reliability_grade": "unreliable",
            "confidence_adjustment": -0.5,
            "warnings": ["Warning A", "Warning B"],
        }
        result = apply_reliability_adjustments(evaluation, reliability)
        assert "Existing warning." in result["warnings"]
        assert "Warning A" in result["warnings"]
        assert "Warning B" in result["warnings"]
