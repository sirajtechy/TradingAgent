"""Load portfolio rules from JSON config."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RULES_PATH = ROOT / "data" / "config" / "portfolio_rules.json"


@dataclass
class PortfolioRules:
    budget: float = 200_000.0
    num_stocks: int = 20
    rebalance_day: int = 21
    universe_mode: str = "top10"
    exit_rank_pct: float = 0.10
    sector_cap_pct: float = 0.25
    single_name_cap_pct: float = 0.10
    min_avg_dollar_volume: float = 500_000.0
    momentum_lookbacks: Dict[str, int] = field(default_factory=dict)
    momentum_weights: Dict[str, float] = field(default_factory=dict)
    conviction_weights: Dict[str, float] = field(default_factory=dict)
    regime_enabled: bool = True
    regime_index: str = "SPY"
    supertrend_period: int = 10
    supertrend_multiplier: float = 2.5
    swing_overlay_enabled: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


def load_rules(path: Optional[Path] = None, overrides: Optional[Dict[str, Any]] = None) -> PortfolioRules:
    cfg_path = path or DEFAULT_RULES_PATH
    raw: Dict[str, Any] = {}
    if cfg_path.is_file():
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    if overrides:
        raw = {**raw, **overrides}

    lookbacks = raw.get("momentum_lookbacks_days") or {
        "1m": 21,
        "3m": 63,
        "6m": 126,
        "9m": 189,
    }
    regime = raw.get("regime") or {}
    swing = raw.get("swing_overlay") or {}

    return PortfolioRules(
        budget=float(raw.get("budget_default", 200_000)),
        num_stocks=int(raw.get("num_stocks", 20)),
        rebalance_day=int(raw.get("rebalance_day_of_month", 21)),
        universe_mode=str(raw.get("universe_mode_default", "top10")),
        exit_rank_pct=float(raw.get("exit_rank_pct", 0.10)),
        sector_cap_pct=float(raw.get("sector_cap_pct", 0.25)),
        single_name_cap_pct=float(raw.get("single_name_cap_pct", 0.10)),
        min_avg_dollar_volume=float(raw.get("min_avg_dollar_volume", 500_000)),
        momentum_lookbacks={str(k): int(v) for k, v in lookbacks.items()},
        momentum_weights={str(k): float(v) for k, v in (raw.get("momentum_weights") or {}).items()},
        conviction_weights={str(k): float(v) for k, v in (raw.get("conviction_weights") or {}).items()},
        regime_enabled=bool(regime.get("enabled", True)),
        regime_index=str(regime.get("index_symbol", "SPY")),
        supertrend_period=int(regime.get("supertrend_period", 10)),
        supertrend_multiplier=float(regime.get("supertrend_multiplier", 2.5)),
        swing_overlay_enabled=bool(swing.get("enabled", False)),
        raw=raw,
    )
