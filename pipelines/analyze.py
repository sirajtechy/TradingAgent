"""
Canonical analyze pipeline — single source for OpenClaw and CLI JSON output.

Batch multi-ticker analyze remains in ``scripts/run_trading.py`` (unchanged behavior).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.contracts.fusion import FusionMode, fuse_by_mode
from core.io.dates import validate_date_iso
from core.paths import ROOT


def default_analyze_json_path(ticker: str, as_of_date: str) -> Path:
    """Default path: ``data/output/research/<date>/<TICKER>_analyze.json``."""
    tk = ticker.strip().upper()
    return ROOT / "data" / "output" / "research" / as_of_date / f"{tk}_analyze.json"


def _write_analyze_json(doc: Dict[str, Any], out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, default=_json_default), encoding="utf-8")
    try:
        return str(out_path.relative_to(ROOT))
    except ValueError:
        return str(out_path)


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
    export_breakdown: bool = False,
    markdown_out: Optional[str] = None,
    json_out: Optional[str] = None,
    refresh_context: bool = False,
    strategy_profile: str = "none",
    technical_pass_only: bool = True,
) -> Dict[str, Any]:
    """
    Point-in-time analysis for one ticker. Returns a JSON-serializable dict.

    Fusion modes: phoenix-fa | phoenix | fundamental | full | technical
    Strategy profiles: none | minervini | moglen | breitstein | mcintosh | blend | all
    """
    tk = ticker.strip().upper()
    as_of = validate_date_iso(as_of_date)
    mode = fusion.strip().lower()
    profile = (strategy_profile or "none").strip().lower()

    def _maybe_save_json(doc: Dict[str, Any]) -> None:
        save_path: Optional[Path] = None
        if json_out:
            save_path = Path(json_out)
        elif export_breakdown or mode in ("full", "full-context", "technical"):
            save_path = default_analyze_json_path(tk, as_of)
        if save_path is not None:
            doc["analyze_json_path"] = _write_analyze_json(doc, save_path)

    def _attach_strategies(doc: Dict[str, Any], px: Optional[Dict] = None, fund: Optional[Dict] = None) -> None:
        if profile == "none":
            return
        if doc.get("technical") and profile in ("blend", "all"):
            tech = doc["technical"]
            doc["strategies"] = {
                "ok": True,
                "ticker": tk,
                "as_of_date": as_of,
                "strategy_profile": profile,
                "layers": tech.get("strategy_layers") or {},
                "meta_signals": (tech.get("technical_fusion") or {}),
                "warnings": tech.get("warnings") or [],
            }
            return
        from agents.strategies.service import analyze_strategies

        doc["strategies"] = analyze_strategies(
            ticker=tk,
            as_of_date=as_of,
            profile=profile,
            phoenix_result=px or doc.get("phoenix"),
            fund_result=fund or doc.get("fundamental"),
            fetch_market_data=True,
        )

    if mode == "technical":
        from agents.technical.service import analyze_technical

        profile_eff = profile if profile != "none" else "blend"
        tech = analyze_technical(ticker=tk, as_of_date=as_of, strategy_profile=profile_eff)
        doc = {
            "ok": tech.get("ok", True),
            "fusion_mode": "technical",
            "ticker": tk,
            "as_of_date": as_of,
            "technical": tech,
            "phoenix": tech.get("phoenix"),
            "pass_enrichment": (tech.get("technical_fusion") or {}).get("pass_enrichment"),
        }
        _attach_strategies(doc)
        _maybe_save_json(doc)
        return doc

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
        doc = {
            "ok": True,
            "fusion_mode": "phoenix-fa",
            "ticker": tk,
            "as_of_date": as_of,
            "fusion": _fusion_to_dict(fus),
            "phoenix": px,
            "fundamental": fund,
        }
        _attach_strategies(doc, px=px, fund=fund)
        _maybe_save_json(doc)
        return doc

    if mode in ("full", "full-context"):
        from agents.orchestrator.agent_breakdown import default_breakdown_markdown_path
        from agents.orchestrator.config import OrchestratorSettings
        from agents.orchestrator.pipeline_full import run_full_analysis

        cfg = OrchestratorSettings(fund_data_source=fund_data_source)
        md_path: Optional[Path] = None
        if export_breakdown or markdown_out:
            md_path = Path(markdown_out) if markdown_out else default_breakdown_markdown_path(tk, as_of)
        full_doc = run_full_analysis(
            ticker=tk,
            as_of_date=as_of,
            fund_data_source=cfg.fund_data_source,
            settings=cfg,
            markdown_out=md_path,
            refresh_context=refresh_context,
            technical_pass_only=technical_pass_only,
            strategy_profile=profile if profile != "none" else "blend",
        )
        if profile != "none" and not full_doc.get("gated"):
            _attach_strategies(full_doc)
        elif full_doc.get("technical"):
            _attach_strategies(full_doc)
        _maybe_save_json(full_doc)
        return full_doc

    if mode == "phoenix":
        from agents.phoenix.service import analyze_ticker as phoenix_analyze

        px = phoenix_analyze(ticker=tk, as_of_date=as_of)
        doc = {
            "ok": True,
            "fusion_mode": "phoenix",
            "ticker": tk,
            "as_of_date": as_of,
            "phoenix": px,
        }
        _attach_strategies(doc, px=px)
        _maybe_save_json(doc)
        return doc

    if mode == "fundamental":
        from agents.fundamental.service import analyze_ticker as fund_analyze

        fund = fund_analyze(ticker=tk, as_of_date=as_of, data_source=fund_data_source)
        doc = {
            "ok": True,
            "fusion_mode": "fundamental",
            "ticker": tk,
            "as_of_date": as_of,
            "fundamental": fund,
        }
        _attach_strategies(doc, fund=fund)
        _maybe_save_json(doc)
        return doc

    raise ValueError(f"Unsupported fusion: {fusion!r}")


def analyze_watchlist(
    *,
    as_of_date: Optional[str] = None,
    fusion: str = "full",
    fund_data_source: str = "yfinance",
    export_breakdown: bool = True,
    refresh_context: bool = False,
    strategy_profile: str = "none",
    signals: Tuple[str, ...] = ("BUY", "WATCH"),
    trade_focus_only: bool = False,
    skip_cached: bool = True,
    max_tickers: Optional[int] = None,
) -> Dict[str, Any]:
    """Run full fusion analyze for all BUY/WATCH tickers from latest master_pilot."""
    from pipelines.watchlist import analyze_json_path, load_watchlist_from_master

    rows, meta = load_watchlist_from_master(
        signal_date=as_of_date,
        signals=signals,
        trade_focus_only=trade_focus_only,
    )
    if meta.get("error") and not rows:
        return {"ok": False, "error": meta["error"], "meta": meta}

    as_of = validate_date_iso(as_of_date or meta.get("signal_date") or "")
    if max_tickers is not None:
        rows = rows[: max(0, int(max_tickers))]

    results: list = []
    for idx, row in enumerate(rows):
        out_path = analyze_json_path(row.ticker, as_of)
        if skip_cached and out_path.is_file():
            try:
                cached = json.loads(out_path.read_text(encoding="utf-8"))
                fusion_doc = cached.get("fusion") or {}
                results.append(
                    {
                        "ticker": row.ticker,
                        "phoenix_signal": row.phoenix_signal,
                        "sector": row.sector,
                        "status": "cached",
                        "analyze_json_path": str(out_path.relative_to(ROOT)),
                        "advisory_verdict": fusion_doc.get("advisory_verdict"),
                        "orchestrator_score": fusion_doc.get("orchestrator_score"),
                    }
                )
                continue
            except (OSError, json.JSONDecodeError):
                pass

        try:
            doc = analyze_single(
                ticker=row.ticker,
                as_of_date=as_of,
                fusion=fusion,
                fund_data_source=fund_data_source,
                export_breakdown=export_breakdown,
                refresh_context=refresh_context and idx == 0,
                strategy_profile=strategy_profile,
            )
            fusion_doc = doc.get("fusion") or {}
            results.append(
                {
                    "ticker": row.ticker,
                    "phoenix_signal": row.phoenix_signal,
                    "sector": row.sector,
                    "status": "ok" if doc.get("ok", True) else "error",
                    "analyze_json_path": doc.get("analyze_json_path"),
                    "advisory_verdict": fusion_doc.get("advisory_verdict"),
                    "orchestrator_score": fusion_doc.get("orchestrator_score"),
                    "error": doc.get("error"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "ticker": row.ticker,
                    "phoenix_signal": row.phoenix_signal,
                    "sector": row.sector,
                    "status": "error",
                    "error": str(exc),
                }
            )

    index = {
        "ok": True,
        "fusion_mode": fusion,
        "as_of_date": as_of,
        "meta": meta,
        "trade_focus_only": trade_focus_only,
        "signals": list(signals),
        "results": results,
        "analyzed": sum(1 for r in results if r.get("status") == "ok"),
        "cached": sum(1 for r in results if r.get("status") == "cached"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
    }
    index_path = ROOT / "data" / "output" / "research" / as_of / "watchlist_analyze.json"
    index["watchlist_index_path"] = _write_analyze_json(index, index_path)
    return index


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
