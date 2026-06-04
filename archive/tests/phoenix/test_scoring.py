"""Phoenix composite score — synthetic snapshots only (no network)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from agents.phoenix.config import PhoenixSettings
from agents.phoenix.models import (
    OHLCVBar,
    PatternMatch,
    PhoenixRequest,
    PhoenixSnapshot,
    SMABundle,
    StageResult,
)
from agents.phoenix.scoring import build_score


def _bar(day: int, close: float, volume: float = 5_000_000.0) -> OHLCVBar:
    d = date(2025, 1, 2) + timedelta(days=day)
    return OHLCVBar(
        bar_date=d,
        open=close - 0.2,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=volume,
    )


def _rising_series(n: int = 160) -> List[OHLCVBar]:
    return [_bar(i, 100.0 + i * 0.08, volume=1_000_000.0 + i * 8000.0) for i in range(n)]


class TestPhoenixBuildScore:
    def test_score_in_bounds_and_buy_when_strong_stage(self):
        bars = _rising_series()
        last = bars[-1]
        smas = SMABundle(
            sma10=last.close - 2.0,
            sma20=last.close - 5.0,
            sma50=last.close - 12.0,
            sma200=last.close - 40.0,
            sma40w=last.close - 38.0,
            sma10_prior=last.close - 2.5,
            sma20_prior=last.close - 6.0,
            sma50_prior=last.close - 13.0,
            sma200_prior=last.close - 42.0,
        )
        snap = PhoenixSnapshot(
            request=PhoenixRequest(ticker="SYN", as_of_date=last.bar_date),
            bars=bars,
            smas=smas,
            vol_avg_20=sum(b.volume for b in bars[-20:]) / 20,
            high_52w=max(b.high for b in bars),
            low_52w=min(b.low for b in bars) * 0.6,
            as_of_price=last.close,
            as_of_price_date=last.bar_date,
            warnings=[],
        )

        stage = StageResult(
            stage=2,
            label="Momentum",
            action="TRADE",
            ma_alignment=True,
            ma_slopes={"sma20": "rising", "sma50": "rising", "sma200": "rising"},
            notes=["synthetic"],
        )

        pattern = PatternMatch(
            pattern_name="VCP",
            confirmed=True,
            volume_confirmed=True,
            pivot_price=last.close + 2.0,
            confidence=0.85,
            vcp_contractions=3,
            base_depth_pct=0.09,
            description="Synthetic VCP breakout",
        )

        score, breakdown, signal = build_score(snap, stage, pattern, PhoenixSettings())

        assert 0.0 <= score <= 100.0
        for key in ("volume", "structure", "pattern", "stage"):
            assert key in breakdown
            assert breakdown[key] >= 0.0

        assert signal in {"BUY", "WATCH", "AVOID"}
        assert score >= 65.0, "Synthetic stage-2 breakout should score bullish tier"
