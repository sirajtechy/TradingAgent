"""Strategy module registry."""

from __future__ import annotations

from typing import Callable, Dict, List

from .models import StrategyContext, StrategySignal

AnalyzeFn = Callable[[StrategyContext], StrategySignal]

STRATEGY_IDS = ("minervini", "moglen", "breitstein", "mcintosh")


def _load_analyzers() -> Dict[str, AnalyzeFn]:
    from agents.strategies.minervini.service import analyze as minervini_analyze
    from agents.strategies.moglen.service import analyze as moglen_analyze
    from agents.strategies.breitstein.service import analyze as breitstein_analyze
    from agents.strategies.mcintosh.service import analyze as mcintosh_analyze

    return {
        "minervini": minervini_analyze,
        "moglen": moglen_analyze,
        "breitstein": breitstein_analyze,
        "mcintosh": mcintosh_analyze,
    }


def resolve_profile(profile: str) -> List[str]:
    p = (profile or "none").strip().lower()
    if p in ("none", ""):
        return []
    if p in ("all", "blend"):
        return list(STRATEGY_IDS)
    if p not in STRATEGY_IDS:
        raise ValueError(
            f"Unknown strategy profile {profile!r}. "
            f"Choose: none, minervini, moglen, breitstein, mcintosh, blend, all."
        )
    return [p]


def run_strategies(ctx: StrategyContext, profile: str) -> Dict[str, dict]:
    ids = resolve_profile(profile)
    if not ids:
        return {}
    analyzers = _load_analyzers()
    out: Dict[str, dict] = {}
    for sid in ids:
        sig = analyzers[sid](ctx)
        out[sid] = sig.to_dict()
    return out
