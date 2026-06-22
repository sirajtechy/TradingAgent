"""Extract and persist technical PASS tickers from master_pilot.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def extract_technical_pass(tickers: Dict[str, Any]) -> Dict[str, Any]:
    """Return tickers where ``pass_enrichment`` is true."""
    passed: Dict[str, Any] = {}
    for sym, row in tickers.items():
        if not isinstance(row, dict):
            continue
        if row.get("pass_enrichment") is True:
            passed[str(sym).upper()] = row
    return passed


def write_technical_pass_from_master(
    master_path: Path,
    *,
    output_path: Optional[Path] = None,
) -> Path:
    """Write ``technical_pass.json`` beside master_pilot or at output_path."""
    doc = json.loads(master_path.read_text(encoding="utf-8"))
    tickers = doc.get("tickers") or {}
    passed = extract_technical_pass(tickers)
    out = output_path or master_path.parent / "technical_pass.json"
    payload = {
        "schema_version": "1.0.0",
        "source": str(master_path.name),
        "signal_date": (doc.get("manifest") or {}).get("signal_date"),
        "pass_count": len(passed),
        "total_tickers": len(tickers),
        "tickers": passed,
    }
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out
