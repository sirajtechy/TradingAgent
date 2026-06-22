"""Technical-agent-only confusion matrix (Phoenix + strategies)."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.evaluation.confusion import build_confusion_payload, confusion_from_rows

# Layers we evaluate in technical-only mode (no FA, macro, news, etc.)
TECHNICAL_AGENT_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("technical", "technical_signal", "signal_correct_technical"),
    ("phoenix", "phoenix_signal", "signal_correct_phoenix"),
    ("minervini", "minervini_signal", "signal_correct_minervini"),
    ("moglen", "moglen_signal", "signal_correct_moglen"),
    ("breitstein", "breitstein_signal", "signal_correct_breitstein"),
    ("mcintosh", "mcintosh_signal", "signal_correct_mcintosh"),
)


def build_technical_confusion_payload(
    rows: Iterable[Dict[str, Any]],
    *,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Confusion matrix for Phoenix + unified technical + strategy layers only."""
    row_list = list(rows)
    by_agent: Dict[str, Any] = {}
    for agent_id, sig_key, corr_key in TECHNICAL_AGENT_SPECS:
        if not any(r.get(corr_key) is not None or r.get(sig_key) for r in row_list):
            continue
        by_agent[agent_id] = confusion_from_rows(
            row_list,
            signal_key=sig_key,
            correct_key=corr_key,
        )

    overall = by_agent.get("technical") or confusion_from_rows(
        row_list,
        signal_key="technical_signal",
        correct_key="signal_correct_technical",
    )
    payload = {
        "meta": {
            **(meta or {}),
            "mode": "technical_only",
            "agents_evaluated": list(by_agent.keys()),
        },
        "cumulative": {
            "overall": overall,
            "by_agent": by_agent,
        },
    }
    payload["diagnostics"] = diagnose_technical_rows(row_list)
    return payload


def diagnose_technical_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """FN tickers and missed-TP (neutral but target hit) for tuning."""
    fn_tickers: List[Dict[str, Any]] = []
    fp_tickers: List[Dict[str, Any]] = []
    missed_tp: List[Dict[str, Any]] = []

    for row in rows:
        sym = row.get("ticker") or "?"
        hit = row.get("target_hit")
        if hit is not True:
            continue

        tech_sig = (row.get("technical_signal") or "neutral").lower()
        tech_ok = row.get("signal_correct_technical")

        if tech_sig == "bearish" and tech_ok is False:
            fn_tickers.append(
                {
                    "ticker": sym,
                    "sector": row.get("sector"),
                    "technical_signal": tech_sig,
                    "phoenix_signal": row.get("phoenix_signal"),
                    "pass_enrichment": (row.get("technical_fusion") or {}).get("pass_enrichment"),
                }
            )
        elif tech_sig == "bullish" and tech_ok is False:
            fp_tickers.append({"ticker": sym, "sector": row.get("sector")})
        elif tech_sig == "neutral":
            missed_tp.append(
                {
                    "ticker": sym,
                    "sector": row.get("sector"),
                    "phoenix_signal": row.get("phoenix_signal"),
                    "pass_enrichment": (row.get("technical_fusion") or {}).get("pass_enrichment"),
                }
            )

    return {
        "false_negatives": fn_tickers,
        "false_negatives_count": len(fn_tickers),
        "false_positives_count": len(fp_tickers),
        "missed_true_positives": missed_tp,
        "missed_true_positives_count": len(missed_tp),
        "targets": {
            "fn_zero": len(fn_tickers) == 0,
            "note": (
                "FN = bearish technical signal when target hit. "
                "Missed TP = neutral signal when target hit (abstained winners)."
            ),
        },
    }


def format_tp_matrix_line(agent_id: str, met: Dict[str, Any]) -> str:
    tp, fp, tn, fn = met.get("TP", 0), met.get("FP", 0), met.get("TN", 0), met.get("FN", 0)
    acc = met.get("accuracy_pct")
    rec = met.get("recall_pct")
    acc_s = f"{acc}%" if acc is not None else "—"
    rec_s = f"{rec}%" if rec is not None else "—"
    fn_flag = " ⚠ FN>0" if fn else ""
    return f"  {agent_id:12}  TP={tp:4}  FP={fp:4}  TN={tn:4}  FN={fn:4}  acc={acc_s:>6}  recall={rec_s:>6}{fn_flag}"


def print_technical_matrix_summary(payload: Dict[str, Any]) -> None:
    """Concise stdout summary after a technical backtest."""
    cum = payload.get("cumulative") or {}
    by_agent = cum.get("by_agent") or {}
    diag = payload.get("diagnostics") or {}

    print()
    print("=" * 72)
    print("TECHNICAL CONFUSION MATRIX (Phoenix + strategies — no FA/intelligence)")
    print("=" * 72)
    order = ["technical", "phoenix", "minervini", "moglen", "breitstein", "mcintosh"]
    for aid in order:
        if aid in by_agent:
            print(format_tp_matrix_line(aid, by_agent[aid]))
    for aid, met in sorted(by_agent.items()):
        if aid not in order:
            print(format_tp_matrix_line(aid, met))

    fn_n = diag.get("false_negatives_count", 0)
    miss_n = diag.get("missed_true_positives_count", 0)
    print("-" * 72)
    if fn_n == 0:
        print(f"✓ False negatives (bearish ∧ target hit): {fn_n}")
    else:
        print(f"✗ False negatives (bearish ∧ target hit): {fn_n}")
        for item in (diag.get("false_negatives") or [])[:10]:
            print(f"    FN  {item.get('ticker')}  phoenix={item.get('phoenix_signal')}")
    print(f"  Missed TP (neutral ∧ target hit): {miss_n}")
    if miss_n and miss_n <= 15:
        for item in (diag.get("missed_true_positives") or [])[:15]:
            print(f"    MISS {item.get('ticker')}  phoenix={item.get('phoenix_signal')}")
    print("=" * 72)
