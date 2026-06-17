"""Load BUY/WATCH tickers from unified master_pilot or reconciled signals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.paths import TRADING_RUNS_DIR, unified_master_dir


@dataclass
class WatchlistTicker:
    ticker: str
    phoenix_signal: str
    sector: str
    phoenix_score: Optional[float]
    fusion_final_signal: Optional[str]
    fusion_orchestrator_score: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "phoenix_signal": self.phoenix_signal,
            "sector": self.sector,
            "phoenix_score": self.phoenix_score,
            "fusion_final_signal": self.fusion_final_signal,
            "fusion_orchestrator_score": self.fusion_orchestrator_score,
        }


def _iter_master_pilot_paths() -> Iterable[Tuple[Path, str]]:
    if not TRADING_RUNS_DIR.is_dir():
        return
    for path in sorted(TRADING_RUNS_DIR.rglob("master_pilot.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        rel = str(path.relative_to(TRADING_RUNS_DIR)).replace("\\", "/")
        yield path, rel


def find_latest_master_pilot(*, prefer_unified: bool = True) -> Optional[Tuple[Path, str, str]]:
    """Return (path, rel_path, signal_date) for newest master_pilot.json."""
    unified: List[Tuple[Path, str, str]] = []
    other: List[Tuple[Path, str, str]] = []
    for path, rel in _iter_master_pilot_paths():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            sig = str((doc.get("manifest") or {}).get("signal_date") or "")[:10]
            if not sig:
                continue
        except (OSError, json.JSONDecodeError):
            continue
        entry = (path, rel, sig)
        if "unified_master_" in rel:
            unified.append(entry)
        else:
            other.append(entry)
    pool = unified if prefer_unified and unified else (unified + other)
    return pool[0] if pool else None


def resolve_master_pilot(signal_date: Optional[str] = None) -> Optional[Tuple[Path, str, str]]:
    if signal_date:
        path = unified_master_dir(signal_date) / "master_pilot.json"
        if path.is_file():
            rel = str(path.relative_to(TRADING_RUNS_DIR)).replace("\\", "/")
            return path, rel, signal_date
        for path, rel in _iter_master_pilot_paths():
            if signal_date in rel:
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    sig = str((doc.get("manifest") or {}).get("signal_date") or signal_date)[:10]
                except (OSError, json.JSONDecodeError):
                    sig = signal_date
                return path, rel, sig
        return None
    return find_latest_master_pilot()


def load_watchlist_from_master(
    *,
    signal_date: Optional[str] = None,
    signals: Sequence[str] = ("BUY", "WATCH"),
    min_phoenix_score: Optional[float] = None,
    trade_focus_only: bool = False,
) -> Tuple[List[WatchlistTicker], Dict[str, Any]]:
    """
    Extract BUY/WATCH tickers from master_pilot.json.

    trade_focus_only: BUY + WATCH with phoenix_score > 60 (matches Phoenix pilot board).
    """
    allowed = {s.strip().upper() for s in signals if s.strip()}
    if not allowed:
        allowed = {"BUY", "WATCH"}

    resolved = resolve_master_pilot(signal_date)
    if not resolved:
        return [], {"error": "No master_pilot.json found. Run ./bin/mts daily or ./bin/mts unified first."}

    path, rel, sig = resolved
    doc = json.loads(path.read_text(encoding="utf-8"))
    tickers_map = doc.get("tickers") or {}

    rows: List[WatchlistTicker] = []
    for tk, row in tickers_map.items():
        if not isinstance(row, dict) or row.get("error"):
            continue
        px = str(row.get("phoenix_signal") or "").upper()
        if px not in allowed:
            continue
        score_raw = row.get("phoenix_score")
        try:
            score = float(score_raw) if score_raw is not None else None
        except (TypeError, ValueError):
            score = None

        if trade_focus_only:
            if px == "WATCH" and (score is None or score <= 60):
                continue
        elif min_phoenix_score is not None and score is not None and score < min_phoenix_score:
            continue

        fusion = row.get("fusion") or {}
        rows.append(
            WatchlistTicker(
                ticker=str(tk).upper(),
                phoenix_signal=px,
                sector=str(row.get("sector") or "Unknown"),
                phoenix_score=score,
                fusion_final_signal=str(fusion.get("final_signal") or "") or None,
                fusion_orchestrator_score=(
                    float(fusion["orchestrator_score"])
                    if fusion.get("orchestrator_score") is not None
                    else None
                ),
            )
        )

    rows.sort(key=lambda r: (0 if r.phoenix_signal == "BUY" else 1, -(r.phoenix_score or 0), r.ticker))

    from core.paths import ROOT

    meta = {
        "signal_date": sig,
        "source_rel": rel,
        "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "buy_count": sum(1 for r in rows if r.phoenix_signal == "BUY"),
        "watch_count": sum(1 for r in rows if r.phoenix_signal == "WATCH"),
        "total": len(rows),
    }
    return rows, meta


def analyze_json_path(ticker: str, as_of_date: str) -> Path:
    from core.paths import ROOT

    return ROOT / "data" / "output" / "research" / as_of_date / f"{ticker.upper()}_analyze.json"
