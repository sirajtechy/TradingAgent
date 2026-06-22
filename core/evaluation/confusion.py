"""Multi-agent confusion matrix builders."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.universe import empty_matrix, matrix_metrics, update_matrix


def mcc(tp: int, fp: int, tn: int, fn: int) -> Optional[float]:
    """Matthews correlation coefficient in [-1, 1]."""
    denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denom <= 0:
        return None
    num = (tp * tn) - (fp * fn)
    return round(num / (denom**0.5), 4)


def confusion_from_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    signal_key: str = "signal",
    correct_key: str = "signal_correct",
) -> Dict[str, Any]:
    """Build confusion counts + metrics from labeled period/ bundle rows."""
    m = empty_matrix()
    for row in rows:
        update_matrix(
            m,
            {
                "signal": row.get(signal_key),
                "signal_correct": row.get(correct_key),
                "error": row.get("error"),
            },
        )
    met = matrix_metrics(m)
    met["mcc"] = mcc(m["TP"], m["FP"], m["TN"], m["FN"])
    return met


# (agent_id, signal_field, correct_field)
AGENT_SIGNAL_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("fusion", "signal", "signal_correct"),
    ("phoenix", "phoenix_signal", "signal_correct_phoenix"),
    ("technical", "technical_signal", "signal_correct_technical"),
    ("fundamental", "fund_signal", "signal_correct_fundamental"),
    ("minervini", "minervini_signal", "signal_correct_minervini"),
    ("moglen", "moglen_signal", "signal_correct_moglen"),
    ("breitstein", "breitstein_signal", "signal_correct_breitstein"),
    ("mcintosh", "mcintosh_signal", "signal_correct_mcintosh"),
    ("fusion_full", "fusion_full_signal", "signal_correct_fusion_full"),
    ("macro", "macro_signal", "signal_correct_macro"),
    ("news", "news_signal", "signal_correct_news"),
    ("insider", "insider_signal", "signal_correct_insider"),
    ("sentiment", "sentiment_signal", "signal_correct_sentiment"),
    ("geopolitics", "geopolitics_signal", "signal_correct_geopolitics"),
)


def build_confusion_payload(
    rows: Iterable[Dict[str, Any]],
    *,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Cumulative overall + per-agent matrices for backtest artifacts."""
    row_list = list(rows)
    by_agent: Dict[str, Any] = {}
    for agent_id, sig_key, corr_key in AGENT_SIGNAL_SPECS:
        if not any(corr_key in r or r.get(corr_key) is not None for r in row_list):
            if not any(sig_key in r for r in row_list):
                continue
        by_agent[agent_id] = confusion_from_rows(
            row_list,
            signal_key=sig_key,
            correct_key=corr_key,
        )

    overall = by_agent.get("fusion") or confusion_from_rows(row_list)
    return {
        "meta": meta or {},
        "cumulative": {
            "overall": overall,
            "by_agent": by_agent,
        },
    }
