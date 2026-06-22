"""Tests for backtest trade level enrichment."""

from __future__ import annotations

from datetime import date, timedelta

from agents.phoenix.models import OHLCVBar, PhoenixRequest, PhoenixSnapshot, SMABundle
from agents.technical.trade_enrichment import enrich_phoenix_for_export


def _snapshot(closes: list[float]) -> PhoenixSnapshot:
    bars = []
    start = date(2024, 1, 1)
    for i, c in enumerate(closes):
        bars.append(
            OHLCVBar(
                bar_date=start + timedelta(days=i),
                open=c * 0.99,
                high=c * 1.01,
                low=c * 0.98,
                close=c,
                volume=1_000_000,
            )
        )
    last = bars[-1]
    return PhoenixSnapshot(
        request=PhoenixRequest(ticker="TEST", as_of_date=last.bar_date),
        bars=bars,
        smas=SMABundle(
            sma10=last.close,
            sma20=last.close,
            sma50=last.close,
            sma200=last.close,
            sma40w=last.close,
            sma10_prior=last.close,
            sma20_prior=last.close,
            sma50_prior=last.close,
            sma200_prior=last.close,
        ),
        vol_avg_20=1_000_000,
        high_52w=last.close * 1.1,
        low_52w=last.close * 0.8,
        as_of_price=last.close,
        as_of_price_date=last.bar_date,
    )


def test_enrich_fills_recovery_trade_levels_and_extension():
    closes = [100.0 + i * 0.5 for i in range(260)]
    snap = _snapshot(closes)
    px = {
        "signal": "WATCH",
        "phoenix_entry_mode": "recovery_upgrade",
        "hard_filter_passed": False,
        "trade_levels": {},
    }
    out = enrich_phoenix_for_export(px, snap)
    tl = out["trade_levels"]
    assert tl["entry_price"] == snap.as_of_price
    assert tl["stop_price"] is not None
    assert tl["target_1"] is not None
    assert tl["target_2"] is not None
    assert out["extension_guardrail"] is not None
    metrics = out["extension_guardrail"].get("metrics") or {}
    assert metrics.get("daily_change_5d_pct") is not None
