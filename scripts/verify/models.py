"""Data models for backtest verification reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

CheckStatus = Literal["PASS", "FAIL", "SKIP", "WARN"]


@dataclass
class VerifyRow:
    """One ticker-period row normalized from any supported artifact format."""

    ticker: str
    signal_date: str
    result_date: str
    entry_price: Optional[float] = None
    start_price_date: Optional[str] = None
    exit_reference_price: Optional[float] = None
    exit_reference_date: Optional[str] = None
    target_price: Optional[float] = None
    target_hit: Optional[bool] = None
    target_hit_date: Optional[str] = None
    fusion_final_signal: Optional[str] = None
    technical_signal: Optional[str] = None
    phoenix_signal: Optional[str] = None
    signal_correct: Optional[bool] = None
    signal_correct_technical: Optional[bool] = None
    signal_correct_phoenix: Optional[bool] = None
    error: Optional[str] = None
    source_artifact: str = ""


@dataclass
class CheckResult:
    """Result of comparing one field."""

    field: str
    status: CheckStatus
    expected: Any = None
    actual: Any = None
    detail: Optional[str] = None


@dataclass
class RowVerification:
    """Verification outcome for a single normalized row."""

    row: VerifyRow
    status: CheckStatus
    checks: List[CheckResult] = field(default_factory=list)


@dataclass
class VerifyReport:
    """Full verification report for one or more artifacts."""

    meta: Dict[str, Any]
    summary: Dict[str, Any]
    rows: List[RowVerification] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "meta": self.meta,
            "summary": self.summary,
            "rows": [
                {
                    "ticker": rv.row.ticker,
                    "signal_date": rv.row.signal_date,
                    "result_date": rv.row.result_date,
                    "status": rv.status,
                    "error": rv.row.error,
                    "artifact": {
                        "entry_price": rv.row.entry_price,
                        "exit_reference_price": rv.row.exit_reference_price,
                        "target_price": rv.row.target_price,
                        "target_hit": rv.row.target_hit,
                        "target_hit_date": rv.row.target_hit_date,
                        "fusion_final_signal": rv.row.fusion_final_signal,
                        "technical_signal": rv.row.technical_signal,
                        "signal_correct": rv.row.signal_correct,
                        "signal_correct_technical": rv.row.signal_correct_technical,
                    },
                    "checks": [
                        {
                            "field": c.field,
                            "status": c.status,
                            "expected": c.expected,
                            "actual": c.actual,
                            "detail": c.detail,
                        }
                        for c in rv.checks
                    ],
                }
                for rv in self.rows
            ],
        }
        if self.meta.get("verified_summary"):
            payload["verified_summary"] = self.meta["verified_summary"]
        return payload
