"""
Canonical analyze pipeline — single source for OpenClaw and CLI JSON output.

Batch multi-ticker analyze remains in ``scripts/run_trading.py`` (unchanged behavior).
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict

from core.contracts.fusion import FusionMode, fuse_by_mode
from core.io.dates import validate_date_iso


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def _fusion_to_dict(fr: Any) -> Dict[str, Any]:
    return dataclasses.asdict(fr)


def analyze_single(
    *,
    ticker: str,
    as_of_date: str,
    fusion: str = "phoenix-fa",
    fund_data_source: str = "yfinance",
) -> Dict[str, Any]:
    """
    Point-in-time analysis for one ticker. Returns a JSON-serializable dict.

    Fusion modes: phoenix-fa | phoenix | fundamental
    """
    tk = ticker.strip().upper()
    as_of = validate_date_iso(as_of_date)
    mode = fusion.strip().lower()

    if mode == "phoenix-fa":
        from agents.fundamental.service import analyze_ticker as fund_analyze
        from agents.orchestrator.config import OrchestratorSettings
        from agents.phoenix.service import analyze_ticker as phoenix_analyze

        cfg = OrchestratorSettings(fund_data_source=fund_data_source)
        px = phoenix_analyze(ticker=tk, as_of_date=as_of)
        fund = fund_analyze(ticker=tk, as_of_date=as_of, data_source=cfg.fund_data_source)
        fus = fuse_by_mode(
            FusionMode.PHOENIX_FUND,
            phoenix_result=px,
            phoenix_error=None,
            fund_result=fund,
            fund_error=None,
            settings=cfg,
        )
        return {
            "ok": True,
            "fusion_mode": "phoenix-fa",
            "ticker": tk,
            "as_of_date": as_of,
            "fusion": _fusion_to_dict(fus),
            "phoenix": px,
            "fundamental": fund,
        }

    if mode == "phoenix":
        from agents.phoenix.service import analyze_ticker as phoenix_analyze

        px = phoenix_analyze(ticker=tk, as_of_date=as_of)
        return {
            "ok": True,
            "fusion_mode": "phoenix",
            "ticker": tk,
            "as_of_date": as_of,
            "phoenix": px,
        }

    if mode == "fundamental":
        from agents.fundamental.service import analyze_ticker as fund_analyze

        fund = fund_analyze(ticker=tk, as_of_date=as_of, data_source=fund_data_source)
        return {
            "ok": True,
            "fusion_mode": "fundamental",
            "ticker": tk,
            "as_of_date": as_of,
            "fundamental": fund,
        }

    raise ValueError(f"Unsupported fusion: {fusion!r}")


def analyze_single_json(
    *,
    ticker: str,
    as_of_date: str,
    fusion: str = "phoenix-fa",
    fund_data_source: str = "yfinance",
    indent: int = 2,
) -> str:
    try:
        doc = analyze_single(
            ticker=ticker,
            as_of_date=as_of_date,
            fusion=fusion,
            fund_data_source=fund_data_source,
        )
        return json.dumps(doc, indent=indent, default=_json_default)
    except Exception as exc:
        doc = {
            "ok": False,
            "fusion_mode": fusion,
            "ticker": ticker.strip().upper(),
            "as_of_date": as_of_date,
            "error": str(exc),
        }
        return json.dumps(doc, indent=indent, default=_json_default)
