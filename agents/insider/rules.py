from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .models import InsiderSnapshot, InsiderTrade


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _classify_trade(t: InsiderTrade) -> str:
    tx = t.transaction_type.lower()
    if "purchase" in tx or "buy" in tx or tx.startswith("p"):
        return "buy"
    if "sale" in tx or "sell" in tx or tx.startswith("s"):
        return "sell"
    return "other"


def _score_net_activity(buys: List[InsiderTrade], sells: List[InsiderTrade]) -> float:
    buy_value = sum(t.value for t in buys)
    sell_value = sum(t.value for t in sells)
    net = buy_value - sell_value
    total = buy_value + sell_value
    if total == 0:
        return 50.0
    ratio = net / total
    if ratio >= 0.5:
        return 75.0
    if ratio >= 0.2:
        return 62.0
    if ratio >= -0.2:
        return 50.0
    if ratio >= -0.5:
        return 38.0
    return 25.0


def _score_cluster_buys(buys: List[InsiderTrade]) -> float:
    """Multiple insiders buying within lookback period is strongly bullish."""
    unique_buyers = len(set(t.owner_name for t in buys if t.owner_name))
    if unique_buyers >= 3:
        return 80.0
    if unique_buyers == 2:
        return 65.0
    if unique_buyers == 1:
        return 55.0
    return 50.0


def _score_executive_signal(buys: List[InsiderTrade], sells: List[InsiderTrade]) -> float:
    """Executive-level insiders carry more weight (CEO, CFO, Director)."""
    exec_keywords = {"ceo", "cfo", "president", "director", "officer", "vp"}

    def _is_exec(t: InsiderTrade) -> bool:
        combined = f"{t.title} {t.owner_name}".lower()
        return any(kw in combined for kw in exec_keywords)

    exec_buys = [t for t in buys if _is_exec(t)]
    exec_sells = [t for t in sells if _is_exec(t)]
    if exec_buys and not exec_sells:
        return 72.0
    if exec_sells and not exec_buys:
        return 32.0
    if exec_buys and exec_sells:
        return 50.0
    return 50.0


def _band_from_score(score: float) -> str:
    if score >= 70:
        return "strong"
    if score >= 58:
        return "good"
    if score >= 45:
        return "mixed"
    if score >= 35:
        return "mixed_negative"
    return "weak"


def _signal_from_score(score: float) -> str:
    if score >= 58:
        return "bullish"
    if score <= 42:
        return "bearish"
    return "neutral"


def evaluate_insider(snapshot: InsiderSnapshot) -> Dict[str, Any]:
    """Deterministic insider trade scoring for a ticker."""
    all_trades = snapshot.trades
    buys = [t for t in all_trades if _classify_trade(t) == "buy"]
    sells = [t for t in all_trades if _classify_trade(t) == "sell"]

    if not all_trades:
        return {
            "signal": "neutral",
            "score": 50.0,
            "band": "mixed",
            "confidence": "low",
            "subscores": {},
            "metrics": {"total_trades": 0, "buy_count": 0, "sell_count": 0},
            "data_quality": "poor",
            "warnings": list(snapshot.warnings),
            "data_sources": list(snapshot.data_sources),
            "bullets": ["• No insider activity in lookback window"],
            "abstain": True,
        }

    subscores: Dict[str, float] = {}
    weights: List[Tuple[str, float]] = []

    net_score = _score_net_activity(buys, sells)
    subscores["net_activity"] = net_score
    weights.append(("net_activity", 0.40))

    cluster_score = _score_cluster_buys(buys)
    subscores["cluster_buys"] = cluster_score
    weights.append(("cluster_buys", 0.30))

    exec_score = _score_executive_signal(buys, sells)
    subscores["executive_signal"] = exec_score
    weights.append(("executive_signal", 0.30))

    total_w = sum(w for _, w in weights)
    score = round(_clamp(sum(subscores[k] * w for k, w in weights) / total_w), 2)
    signal = _signal_from_score(score)
    band = _band_from_score(score)

    buy_value = sum(t.value for t in buys)
    sell_value = sum(t.value for t in sells)
    data_quality = "good" if len(all_trades) >= 3 else "fair"

    bullets = _build_bullets(buys, sells, buy_value, sell_value, signal)

    return {
        "signal": signal,
        "score": score,
        "band": band,
        "confidence": "high" if len(all_trades) >= 5 else "medium",
        "subscores": subscores,
        "metrics": {
            "total_trades": len(all_trades),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "buy_value": round(buy_value, 2),
            "sell_value": round(sell_value, 2),
            "net_value": round(buy_value - sell_value, 2),
        },
        "data_quality": data_quality,
        "warnings": list(snapshot.warnings),
        "data_sources": list(snapshot.data_sources),
        "bullets": bullets,
        "abstain": False,
    }


def _build_bullets(
    buys: List[InsiderTrade],
    sells: List[InsiderTrade],
    buy_value: float,
    sell_value: float,
    signal: str,
) -> List[str]:
    bullets: List[str] = []
    if buys:
        unique = len(set(t.owner_name for t in buys if t.owner_name))
        bullets.append(f"• {len(buys)} insider buy(s) by {unique} insider(s), ${buy_value:,.0f}")
    if sells:
        bullets.append(f"• {len(sells)} insider sale(s), ${sell_value:,.0f}")
    bullets.append(f"• Insider signal: {signal}")
    return bullets[:3]
