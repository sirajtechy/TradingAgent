"""
graph.py — LangGraph 8-node pipeline for the Phoenix Agent.

Pipeline topology:
  START
    → fetch_data          Node 1: Polygon OHLCV → PhoenixSnapshot
    → apply_hard_filters  Node 2: 200DMA + 52w-low gate (fail-fast on AVOID)
    → classify_stage      Node 3: Stage 1/2/3/4 (fail-fast if not Stage 2)
    → detect_patterns     Node 4: VCP / Flat Base / Tight Flag / Shakeout / Pullback
    → evaluate_entry      Node 5: 4 entry type mappers + entry price
    → compute_risk        Node 6: LOC stop / targets / R/R / position size
    → build_score         Node 7: Phoenix composite score 0–100
    → render_report       Node 8: assemble PhoenixSignal + human-readable text
  END

Fail-fast exits (via conditional edges):
  apply_hard_filters → render_report (AVOID) if hard filter fails
  classify_stage     → render_report (WATCH/AVOID) if stage2_only and not Stage 2

The pipeline never raises on expected exits — HardFilterRejected and
StageFilterRejected are caught inside the nodes and stored in state so
render_report can produce a complete (partial) PhoenixSignal.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import PhoenixSettings
from .data_client import PhoenixDataClient
from .entry import evaluate_entry
from .exceptions import HardFilterRejected, StageFilterRejected
from .filters import FilterResult, apply_hard_filters
from .models import (
    EntrySetup,
    OHLCVBar,
    PatternMatch,
    PhoenixRequest,
    PhoenixSignal,
    PhoenixSnapshot,
    RiskLevels,
    StageResult,
)
from .patterns import detect_all_patterns
from .extension import compute_extension_guardrail
from .reporting import build_text_report
from .risk import compute_risk as _compute_risk
from .scoring import build_score
from .stage_classifier import classify_stage


# ─────────────────────────────────────────────────────────────────────────────
# State schema
# ─────────────────────────────────────────────────────────────────────────────

class PhoenixState(TypedDict, total=False):
    """Typed state flowing through the Phoenix pipeline."""

    # Input
    request: PhoenixRequest
    settings: PhoenixSettings
    account_size: float

    # Node 1 output
    snapshot: PhoenixSnapshot

    # Node 2 output
    filter_result: FilterResult
    hard_filter_passed: bool
    hard_filter_reason: Optional[str]
    early_exit: bool          # True → skip to render_report

    # Node 3 output
    stage: StageResult
    stage_exit: bool          # True → not Stage 2, skip to render_report

    # Node 4 output
    pattern: PatternMatch

    # Node 5 output
    entry: EntrySetup

    # Node 6 output
    risk: RiskLevels

    # Node 7 output
    score: float
    score_breakdown: Dict[str, float]
    signal: str               # BUY / WATCH / AVOID

    # Node 8 output
    phoenix_signal: PhoenixSignal
    report: str

    # Accumulated warnings
    warnings: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Sentinel models for fail-fast exits
# ─────────────────────────────────────────────────────────────────────────────

def _avoid_stage(stage_num: int, label: str, action: str) -> StageResult:
    return StageResult(
        stage=stage_num,
        label=label,
        action=action,
        ma_alignment=False,
        ma_slopes={},
        notes=[f"Early exit: Stage {stage_num} — {label} ({action})"],
    )


def _no_pattern() -> PatternMatch:
    return PatternMatch(
        pattern_name="None",
        confirmed=False,
        volume_confirmed=False,
        pivot_price=0.0,
        confidence=0.0,
        vcp_contractions=0,
        base_depth_pct=0.0,
        description="Pipeline exited before pattern detection.",
    )


def _no_entry(price: float = 0.0) -> EntrySetup:
    return EntrySetup(
        entry_type="none",
        entry_price=price,
        trigger_description="Pipeline exited before entry evaluation.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph(
    client: Optional[PhoenixDataClient] = None,
    settings: Optional[PhoenixSettings] = None,
) -> Any:
    """
    Construct and compile the Phoenix LangGraph pipeline.

    Args:
        client:   PhoenixDataClient; a new one is created if None.
        settings: PhoenixSettings; defaults are used if None.

    Returns:
        A compiled LangGraph runnable that accepts
        ``{"request": PhoenixRequest, "settings": PhoenixSettings,
           "account_size": float}``
        and produces ``{"phoenix_signal": PhoenixSignal}``.
    """
    _client   = client   or PhoenixDataClient()
    _settings = settings or PhoenixSettings()

    graph = StateGraph(PhoenixState)

    # ── Node 1: fetch_data ─────────────────────────────────────────────────
    def fetch_data_node(state: PhoenixState) -> Dict[str, Any]:
        req      = state["request"]
        cfg      = state.get("settings") or _settings
        warnings = list(state.get("warnings") or [])
        try:
            snap = _client.build_snapshot(req.ticker, req.as_of_date, cfg)
            warnings.extend(snap.warnings)
        except Exception as exc:
            # Return a minimal state so render_report can produce an error signal
            return {
                "snapshot": None,
                "hard_filter_passed": False,
                "hard_filter_reason": f"Data fetch failed: {exc}",
                "early_exit": True,
                "warnings": warnings + [str(exc)],
            }
        return {"snapshot": snap, "warnings": warnings, "early_exit": False}

    # ── Node 2: apply_hard_filters ─────────────────────────────────────────
    def apply_hard_filters_node(state: PhoenixState) -> Dict[str, Any]:
        snap = state.get("snapshot")
        cfg  = state.get("settings") or _settings

        if snap is None or state.get("early_exit"):
            return {"hard_filter_passed": False, "early_exit": True}

        filt = apply_hard_filters(snap, cfg, raise_on_fail=False)
        return {
            "filter_result":      filt,
            "hard_filter_passed": filt.passed,
            "hard_filter_reason": filt.failure_reason,
            "early_exit":         not filt.passed,
        }

    # ── Node 3: classify_stage ─────────────────────────────────────────────
    def classify_stage_node(state: PhoenixState) -> Dict[str, Any]:
        snap = state.get("snapshot")
        cfg  = state.get("settings") or _settings

        if snap is None or state.get("early_exit"):
            return {"stage": _avoid_stage(4, "Decline", "AVOID"), "stage_exit": True}

        stg = classify_stage(snap, cfg)

        # Fail-fast if stage2_only and not Stage 2
        if cfg.stage2_only and stg.stage != 2:
            return {"stage": stg, "stage_exit": True, "early_exit": True}

        return {"stage": stg, "stage_exit": False}

    # ── Node 4: detect_patterns ────────────────────────────────────────────
    def detect_patterns_node(state: PhoenixState) -> Dict[str, Any]:
        snap = state.get("snapshot")
        cfg  = state.get("settings") or _settings

        if snap is None or state.get("early_exit"):
            return {"pattern": _no_pattern()}

        pat = detect_all_patterns(snap, cfg)
        return {"pattern": pat}

    # ── Node 5: evaluate_entry ─────────────────────────────────────────────
    def evaluate_entry_node(state: PhoenixState) -> Dict[str, Any]:
        snap = state.get("snapshot")
        pat  = state.get("pattern") or _no_pattern()
        cfg  = state.get("settings") or _settings

        if snap is None or state.get("early_exit"):
            return {"entry": _no_entry()}

        ent = evaluate_entry(pat, snap, cfg)
        return {"entry": ent}

    # ── Node 6: compute_risk ───────────────────────────────────────────────
    def compute_risk_node(state: PhoenixState) -> Dict[str, Any]:
        snap         = state.get("snapshot")
        pat          = state.get("pattern")  or _no_pattern()
        ent          = state.get("entry")    or _no_entry()
        cfg          = state.get("settings") or _settings
        account_size = state.get("account_size") or 100_000

        if snap is None or state.get("early_exit") or ent.entry_type == "none":
            return {"risk": None}

        rsk = _compute_risk(ent, pat, snap, cfg, account_size)
        return {"risk": rsk}

    # ── Node 7: build_score ────────────────────────────────────────────────
    def build_score_node(state: PhoenixState) -> Dict[str, Any]:
        snap = state.get("snapshot")
        stg  = state.get("stage")   or _avoid_stage(4, "Decline", "AVOID")
        pat  = state.get("pattern") or _no_pattern()
        cfg  = state.get("settings") or _settings

        # Hard filter failure: no data → score 0, AVOID
        if snap is None or not state.get("hard_filter_passed", True):
            return {"score": 0.0, "score_breakdown": {}, "signal": "AVOID"}

        # Stage exit (Stage 1/3/4): still compute the score so the caller
        # can see how close the stock is to a BUY threshold.
        sc, bd, sig = build_score(snap, stg, pat, cfg)
        return {"score": sc, "score_breakdown": bd, "signal": sig}

    # ── Node 8: render_report ──────────────────────────────────────────────
    def render_report_node(state: PhoenixState) -> Dict[str, Any]:
        req      = state["request"]
        snap     = state.get("snapshot")
        stg      = state.get("stage") or _avoid_stage(4, "Decline", "AVOID")
        pat      = state.get("pattern")
        ent      = state.get("entry")
        rsk      = state.get("risk")
        score    = state.get("score") or 0.0
        bd       = state.get("score_breakdown") or {}
        signal   = state.get("signal") or "AVOID"
        warnings = state.get("warnings") or []

        # Override signal for hard/stage filter exits
        if not state.get("hard_filter_passed", True):
            signal = "AVOID"
        elif state.get("stage_exit"):
            signal = "WATCH" if stg.stage == 1 else "AVOID"

        ext_guard: Optional[Dict[str, Any]] = None
        ext_warnings: List[str] = list(warnings)
        if snap is not None and state.get("hard_filter_passed", True):
            ext_guard = compute_extension_guardrail(snap, pat, state.get("settings") or _settings)
            if ext_guard.get("chase_risk") in ("moderate", "elevated"):
                ext_warnings.append(str(ext_guard.get("summary") or ""))

        phoenix_signal = PhoenixSignal(
            ticker=req.ticker,
            as_of_date=req.as_of_date,
            signal=signal,
            stage=stg,
            pattern=pat,
            entry=ent,
            risk=rsk,
            score=score,
            score_breakdown=bd,
            hard_filter_passed=state.get("hard_filter_passed", False),
            hard_filter_reason=state.get("hard_filter_reason"),
            report="",
            warnings=ext_warnings,
            extension_guardrail=ext_guard,
        )

        report_text = build_text_report(phoenix_signal)
        phoenix_signal.report = report_text

        return {"phoenix_signal": phoenix_signal, "report": report_text}

    # ── Register nodes ─────────────────────────────────────────────────────
    graph.add_node("fetch_data",          fetch_data_node)
    graph.add_node("apply_hard_filters",  apply_hard_filters_node)
    graph.add_node("classify_stage",      classify_stage_node)
    graph.add_node("detect_patterns",     detect_patterns_node)
    graph.add_node("evaluate_entry",      evaluate_entry_node)
    graph.add_node("compute_risk",        compute_risk_node)
    graph.add_node("build_score",         build_score_node)
    graph.add_node("render_report",       render_report_node)

    # ── Linear backbone ────────────────────────────────────────────────────
    graph.add_edge(START,               "fetch_data")
    graph.add_edge("fetch_data",        "apply_hard_filters")

    # ── Conditional: hard filter fail-fast ─────────────────────────────────
    def _after_hard_filter(state: PhoenixState) -> str:
        return "render_report" if state.get("early_exit") else "classify_stage"

    graph.add_conditional_edges(
        "apply_hard_filters",
        _after_hard_filter,
        {"classify_stage": "classify_stage", "render_report": "render_report"},
    )

    # ── Conditional: stage filter fail-fast ────────────────────────────────
    # Stage exits still go through build_score so the caller gets a
    # meaningful partial score (e.g. DELL Stage 1 shows 35/100 not 0).
    def _after_stage(state: PhoenixState) -> str:
        return "build_score" if state.get("stage_exit") else "detect_patterns"

    graph.add_conditional_edges(
        "classify_stage",
        _after_stage,
        {"detect_patterns": "detect_patterns", "build_score": "build_score"},
    )

    # ── Remaining linear edges ─────────────────────────────────────────────
    graph.add_edge("detect_patterns", "evaluate_entry")
    graph.add_edge("evaluate_entry",  "compute_risk")
    graph.add_edge("compute_risk",    "build_score")
    graph.add_edge("build_score",     "render_report")
    graph.add_edge("render_report",   END)

    return graph.compile()
