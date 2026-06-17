"""Geopolitics client: FMP when available, yfinance news scan fallback (free)."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from .config import GeopoliticsSettings, load_settings
from .fmp_client import FMPGeopoliticsClient
from .models import GeopoliticsSnapshot
from .yfinance_fallback import build_snapshot as yfinance_snapshot


class CompositeGeopoliticsClient:
    def __init__(self, settings: Optional[GeopoliticsSettings] = None) -> None:
        self._settings = settings or GeopoliticsSettings(api_key="unused")
        self._fmp: FMPGeopoliticsClient | None = None
        if settings and settings.api_key and settings.api_key != "unused":
            self._fmp = FMPGeopoliticsClient(settings)

    def build_snapshot(self, as_of_date: date) -> GeopoliticsSnapshot:
        prefer = os.getenv("GEOPOLITICS_DATA_SOURCE", "auto").strip().lower()

        if prefer == "yfinance":
            return yfinance_snapshot(as_of_date, settings=self._settings)

        if self._fmp and prefer in ("auto", "fmp"):
            try:
                snap = self._fmp.build_snapshot(as_of_date)
                if snap.headlines or snap.total_scanned:
                    return snap
            except Exception as exc:
                msg = str(exc)
                if "402" in msg or "Payment Required" in msg:
                    snap = yfinance_snapshot(as_of_date, settings=self._settings)
                    snap.warnings.insert(0, "FMP geopolitics feeds require paid tier (402) — using yfinance scan.")
                    return snap

        return yfinance_snapshot(as_of_date, settings=self._settings)


def load_composite_client(api_key: str | None = None) -> CompositeGeopoliticsClient:
    key = api_key or os.getenv("FMP_API_KEY")
    if key:
        try:
            return CompositeGeopoliticsClient(load_settings(api_key=key))
        except Exception:
            pass
    return CompositeGeopoliticsClient(None)
