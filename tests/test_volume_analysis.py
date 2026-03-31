"""
test_volume_analysis.py — Tests for the sector-relative volume analysis module.

Uses synthetic volume data so no network calls are needed.
"""

import pytest

from technical_agent.volume_analysis import (
    SECTOR_PEERS,
    analyze_sector_relative_volume,
    build_volume_analysis_report,
    compute_volume_metrics,
    get_sector_peers,
)


# ====================================================================== #
# get_sector_peers                                                         #
# ====================================================================== #

class TestGetSectorPeers:

    def test_known_sector_returns_peers(self):
        peers = get_sector_peers("Technology", "AAPL")
        assert isinstance(peers, list)
        assert len(peers) > 0
        assert "AAPL" not in peers

    def test_target_excluded(self):
        peers = get_sector_peers("Energy", "XOM")
        assert "XOM" not in peers

    def test_case_insensitive_exclusion(self):
        peers = get_sector_peers("Technology", "aapl")
        assert "AAPL" not in peers

    def test_unknown_sector_returns_empty(self):
        peers = get_sector_peers("Alien Technology", "AAPL")
        assert peers == []

    def test_all_sectors_defined(self):
        assert len(SECTOR_PEERS) >= 10


# ====================================================================== #
# compute_volume_metrics                                                   #
# ====================================================================== #

class TestComputeVolumeMetrics:

    def test_normal_volume_series(self):
        volumes = [1_000_000.0] * 30
        result = compute_volume_metrics(volumes)
        assert result["avg_volume_20d"] == 1_000_000
        assert result["latest_volume"] == 1_000_000
        assert result["relative_volume_ratio"] == 1.0
        assert result["volume_trend"] == "flat"
        assert result["volume_std_20d"] is not None

    def test_rising_volume_trend(self):
        # First 15 days low, last 15 days high
        volumes = [500_000.0] * 15 + [2_000_000.0] * 15
        result = compute_volume_metrics(volumes, window=20)
        assert result["volume_trend"] == "rising"

    def test_falling_volume_trend(self):
        volumes = [2_000_000.0] * 15 + [500_000.0] * 15
        result = compute_volume_metrics(volumes, window=20)
        assert result["volume_trend"] == "falling"

    def test_insufficient_data(self):
        volumes = [100.0] * 5
        result = compute_volume_metrics(volumes, window=20)
        assert result["avg_volume_20d"] is None
        assert result["latest_volume"] == 100.0

    def test_empty_volumes(self):
        result = compute_volume_metrics([])
        assert result["avg_volume_20d"] is None
        assert result["latest_volume"] is None


# ====================================================================== #
# analyze_sector_relative_volume                                           #
# ====================================================================== #

class TestAnalyzeSectorRelativeVolume:

    def test_normal_volume_in_sector(self):
        ticker_volumes = {
            "AAPL": 50_000_000.0,
            "MSFT": 30_000_000.0,
            "GOOGL": 25_000_000.0,
            "META": 20_000_000.0,
            "TEST": 35_000_000.0,
        }
        result = analyze_sector_relative_volume(ticker_volumes, "TEST")
        assert result["percentile_rank"] is not None
        assert result["is_anomalous"] is False
        assert result["z_score"] is not None

    def test_anomalously_high_volume(self):
        ticker_volumes = {
            "A": 1_000_000.0,
            "B": 1_100_000.0,
            "C": 900_000.0,
            "D": 1_050_000.0,
            "TARGET": 50_000_000.0,  # 50x peers
        }
        result = analyze_sector_relative_volume(ticker_volumes, "TARGET")
        assert result["is_anomalous"] is True
        assert result["anomaly_direction"] == "above"

    def test_target_missing_volume(self):
        ticker_volumes = {"A": 1_000_000.0, "B": 2_000_000.0}
        result = analyze_sector_relative_volume(ticker_volumes, "MISSING")
        assert result["percentile_rank"] is None
        assert "unavailable" in result["warnings"][0].lower()

    def test_no_peers(self):
        ticker_volumes = {"TARGET": 1_000_000.0}
        result = analyze_sector_relative_volume(ticker_volumes, "TARGET")
        assert result["percentile_rank"] is None
        assert result["is_anomalous"] is False

    def test_few_peers_warning(self):
        ticker_volumes = {
            "A": 1_000_000.0,
            "B": 2_000_000.0,
            "TARGET": 1_500_000.0,
        }
        result = analyze_sector_relative_volume(ticker_volumes, "TARGET")
        assert any("peers" in w.lower() for w in result.get("warnings", []))


# ====================================================================== #
# build_volume_analysis_report                                             #
# ====================================================================== #

class TestBuildVolumeAnalysisReport:

    def test_report_structure(self):
        stock_metrics = compute_volume_metrics([1_000_000.0] * 30)
        sector_analysis = analyze_sector_relative_volume(
            {"AAPL": 50e6, "TEST": 1e6}, "TEST"
        )
        report = build_volume_analysis_report(
            "TEST", stock_metrics, sector_analysis, "Technology"
        )
        assert report["ticker"] == "TEST"
        assert report["sector"] == "Technology"
        assert "stock_volume" in report
        assert "sector_comparison" in report
        assert "summary" in report
        assert isinstance(report["summary"], str)
