"""
Phoenix pattern detection public API.

Phoenix Trader uses 5 structural patterns (in priority order):
  1. VCP - Volatility Contraction Pattern (primary, Mark Minervini)
  2. Flat Base - 4-24 weeks sideways, <15% range, volume contracting
  3. Tight Flag - sharp flagpole + tight consolidation + volume dryup
  4. Shakeout - false breakdown below support, then snap back above
  5. Pullback to MA10/MA20 - healthy retrace after a prior breakout

Public API:
  detect_all_patterns(snapshot, settings) -> PatternMatch
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..config import PhoenixSettings
from ..models import PatternMatch, PhoenixSnapshot
from ..pattern_helpers import _no_pattern
from .flat_base import _detect_flat_base
from .pullback import _detect_pullback
from .shakeout import _detect_shakeout
from .tight_flag import _detect_tight_flag
from .vcp import _detect_vcp

__all__ = ["detect_all_patterns"]


def detect_all_patterns(
    snapshot: PhoenixSnapshot,
    settings: Optional[PhoenixSettings] = None,
) -> PatternMatch:
    """
    Run all 5 pattern detectors and return the best (highest confidence) match.

    Priority order when confidence is equal:
      VCP > Flat Base > Tight Flag > Shakeout > Pullback

    Returns a PatternMatch with pattern_name='None' if nothing qualifies.
    """
    if settings is None:
        settings = PhoenixSettings()

    bars = snapshot.bars
    vol_avg_20 = snapshot.vol_avg_20
    sma10 = snapshot.smas.sma10
    sma20 = snapshot.smas.sma20

    candidates: List[Tuple[int, PatternMatch]] = []  # (priority, match)

    # Priority 1 - VCP
    vcp = _detect_vcp(bars, vol_avg_20, settings)
    if vcp is not None:
        candidates.append((1, vcp))

    # Priority 2 - Flat Base
    flat = _detect_flat_base(bars, vol_avg_20, settings)
    if flat is not None:
        candidates.append((2, flat))

    # Priority 3 - Tight Flag
    flag = _detect_tight_flag(bars, vol_avg_20, settings)
    if flag is not None:
        candidates.append((3, flag))

    # Priority 4 - Shakeout
    shakeout = _detect_shakeout(bars, vol_avg_20, sma20, settings)
    if shakeout is not None:
        candidates.append((4, shakeout))

    # Priority 5 - Pullback
    pullback = _detect_pullback(bars, vol_avg_20, sma10, sma20, settings)
    if pullback is not None:
        candidates.append((5, pullback))

    if not candidates:
        return _no_pattern()

    # Sort: highest confidence first; break ties by priority (lower = better)
    candidates.sort(key=lambda x: (-x[1].confidence, x[0]))
    return candidates[0][1]
