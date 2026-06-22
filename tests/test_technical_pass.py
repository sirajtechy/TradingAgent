"""Technical pass extraction from master_pilot."""

from __future__ import annotations

import json
from pathlib import Path

from pipelines.technical_pass import extract_technical_pass


def test_extract_technical_pass():
    tickers = {
        "AAPL": {"pass_enrichment": True, "phoenix_signal": "BUY"},
        "MSFT": {"pass_enrichment": False},
        "NVDA": {"pass_enrichment": True, "resilience_score": 72},
    }
    passed = extract_technical_pass(tickers)
    assert set(passed.keys()) == {"AAPL", "NVDA"}


def test_write_technical_pass_from_master(tmp_path: Path):
    master = tmp_path / "master_pilot.json"
    master.write_text(
        json.dumps(
            {
                "manifest": {"signal_date": "2025-09-01"},
                "tickers": {
                    "AAPL": {"pass_enrichment": True},
                    "MSFT": {"pass_enrichment": False},
                },
            }
        ),
        encoding="utf-8",
    )
    from pipelines.technical_pass import write_technical_pass_from_master

    out = write_technical_pass_from_master(master)
    doc = json.loads(out.read_text())
    assert doc["pass_count"] == 1
    assert "AAPL" in doc["tickers"]
