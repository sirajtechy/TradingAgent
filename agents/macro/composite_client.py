"""Macro data client: FRED when available, yfinance proxy fallback (free)."""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class MacroDataClient(Protocol):
    def build_snapshot(self, as_of_date: date) -> Tuple[Dict[str, Any], List[str], List[str]]: ...


class CompositeMacroClient:
    def build_snapshot(self, as_of_date: date) -> Tuple[Dict[str, Any], List[str], List[str]]:
        prefer = os.getenv("MACRO_DATA_SOURCE", "auto").strip().lower()

        if prefer == "yfinance":
            from .yfinance_fallback import build_snapshot as yf_build

            return yf_build(as_of_date)

        fred_key = os.getenv("FRED_API_KEY")
        if fred_key and prefer in ("auto", "fred"):
            try:
                from .config import MacroSettings
                from .fred_client import FREDClient

                client = FREDClient(MacroSettings(api_key=fred_key))
                metrics, sources, warnings = client.build_snapshot(as_of_date)
                if sources:
                    return metrics, sources, warnings
            except Exception:
                pass

        from .yfinance_fallback import build_snapshot as yf_build

        return yf_build(as_of_date)
