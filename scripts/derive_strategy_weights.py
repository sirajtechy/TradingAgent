#!/usr/bin/env python3
"""
derive_strategy_weights.py — Derive ML meta-learner weights from backtest results.

Reads per-strategy accuracy from one or more prediction_backtest_summary.json files
and computes data-driven weights for the ml_layer() function in strategies.py.

Algorithm:
  1. Aggregate per-strategy accuracy across all available backtest summaries that
     match the requested horizon_days (or all horizons if --all-horizons is set).
  2. Apply a minimum-sample floor: strategies with fewer than MIN_SAMPLES
     directional signals revert to the baseline weight (uniform 1/N share).
  3. Normalise accuracy scores to weights via min-max scaling followed by
     softmax to keep the distribution smooth and prevent a single dominant strategy
     from collapsing all other weights to near-zero.
  4. Write the result to agents/prediction/strategy_weights.json, keyed by
     horizon_days so multiple horizons can coexist.

Usage:
  python scripts/derive_strategy_weights.py
  python scripts/derive_strategy_weights.py --horizon 60
  python scripts/derive_strategy_weights.py --all-horizons
  python scripts/derive_strategy_weights.py --dry-run        # print only, no write

Output file format:
  {
    "30": {                          # horizon_days key
      "EMA Crossover": 0.123,
      "MACD + RSI":    0.089,
      ...
    },
    "60": { ... }
  }

The ml_layer() function in strategies.py will load this file on first call
and cache the result.  If the file is absent or corrupt, it falls back to
the hardcoded defaults without crashing.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Project root on sys.path ────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
import paths

# ── Strategy names (must match exactly what backtester.py records) ───────────
_ALL_STRATEGY_NAMES: List[str] = [
    "EMA Crossover",
    "MACD + RSI",
    "Bollinger Squeeze",
    "Supertrend",
    "OBV Divergence",
    "S/R Breakout",
    "RSI Divergence",
    "Mean Reversion",
    "Ichimoku Cloud",
    "ML Meta-Learner (XGBoost proxy)",
]

# Minimum number of directional signals required before a strategy's measured
# accuracy is trusted.  Below this threshold, the strategy receives the
# baseline weight (uniform share among all strategies).
MIN_SAMPLES: int = 20

# Softmax temperature — higher = smoother / more uniform; lower = sharper peaks.
# 1.0 gives standard softmax.  We use 2.0 to avoid extreme concentration.
SOFTMAX_TEMPERATURE: float = 2.0

# Weights output file
_WEIGHTS_FILE: Path = _ROOT / "agents" / "prediction" / "strategy_weights.json"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _softmax(values: List[float], temperature: float = 1.0) -> List[float]:
    """Compute temperature-scaled softmax over *values*."""
    scaled = [v / temperature for v in values]
    max_v = max(scaled)
    exps = [math.exp(v - max_v) for v in scaled]  # numerically stable
    total = sum(exps)
    return [e / total for e in exps]


def _uniform_weights(n: int) -> List[float]:
    """Return uniform weights summing to 1.0 over n strategies."""
    return [1.0 / n] * n


def _load_summary(path: Path) -> Optional[Dict]:
    """Load and validate a prediction_backtest_summary.json file.
    Returns None if file is missing, unreadable, or missing required keys.
    """
    try:
        data = json.loads(path.read_text())
        if "strategy_accuracy" not in data:
            return None
        return data
    except Exception:
        return None


def _find_summary_files(pred_backtest_dir: Path) -> List[Path]:
    """Return all prediction_backtest_summary.json files under *pred_backtest_dir*."""
    return sorted(pred_backtest_dir.rglob("prediction_backtest_summary.json"))


def _aggregate_accuracy(
    summary_files: List[Path],
    target_horizon: Optional[int] = None,
) -> Tuple[Dict[str, Dict], int]:
    """
    Aggregate per-strategy accuracy across multiple summary files.

    Args:
        summary_files:   List of paths to summary JSON files.
        target_horizon:  If set, only include summaries with matching horizon_days.
                         If None, aggregate all found summaries (mixed-horizon).

    Returns:
        (aggregated_stats, n_summaries_used)
        aggregated_stats: {strategy_name: {"correct": int, "total": int, "accuracy_pct": float}}
    """
    totals: Dict[str, Dict] = defaultdict(lambda: {"correct": 0, "total": 0})
    n_used = 0

    for path in summary_files:
        data = _load_summary(path)
        if data is None:
            continue
        # Horizon filter
        horizon = data.get("horizon_days")
        if target_horizon is not None and horizon != target_horizon:
            continue
        n_used += 1
        for strat, stats in data["strategy_accuracy"].items():
            totals[strat]["correct"] += stats.get("correct", 0)
            totals[strat]["total"]   += stats.get("total_directional", 0)

    # Compute aggregated accuracy
    result: Dict[str, Dict] = {}
    for strat, s in totals.items():
        acc = (s["correct"] / s["total"] * 100.0) if s["total"] > 0 else 50.0
        result[strat] = {
            "correct": s["correct"],
            "total_directional": s["total"],
            "accuracy_pct": round(acc, 2),
        }

    return result, n_used


def derive_weights(
    aggregated: Dict[str, Dict],
    strategy_names: List[str],
    min_samples: int = MIN_SAMPLES,
    temperature: float = SOFTMAX_TEMPERATURE,
    verbose: bool = True,
) -> Dict[str, float]:
    """
    Convert aggregated accuracy stats to normalised strategy weights.

    Steps:
      1. For strategies with total_directional < min_samples, mark as
         "unreliable" and assign them the baseline weight.
      2. For reliable strategies, collect accuracy_pct values.
      3. Run temperature-scaled softmax on accuracy values to produce weights.
      4. The final dict sums to 1.0.  Unreliable strategies receive the
         same share as the average softmax weight (uniform baseline).
    """
    reliable: List[Tuple[str, float]] = []  # (name, accuracy_pct)
    unreliable: List[str] = []

    for name in strategy_names:
        stats = aggregated.get(name)
        if stats is None or stats["total_directional"] < min_samples:
            unreliable.append(name)
            if verbose:
                total = stats["total_directional"] if stats else 0
                print(f"  [BASELINE] {name:<40} n={total:>4}  (< {min_samples} threshold)")
        else:
            reliable.append((name, stats["accuracy_pct"]))
            if verbose:
                print(
                    f"  [RELIABLE] {name:<40} "
                    f"acc={stats['accuracy_pct']:>5.1f}%  n={stats['total_directional']:>4}"
                )

    n_total = len(strategy_names)
    if not reliable:
        # All strategies are unreliable — fall back to uniform
        if verbose:
            print("\n  Warning: No strategies met the minimum-sample threshold. "
                  "Using uniform weights.")
        return {name: round(1.0 / n_total, 6) for name in strategy_names}

    # Compute softmax over reliable strategies' accuracy values
    reliable_names = [r[0] for r in reliable]
    reliable_accs  = [r[1] for r in reliable]
    reliable_weights = _softmax(reliable_accs, temperature=temperature)

    # Baseline weight: average weight that would be allocated to each strategy
    # if all were reliable.  Unreliable strategies get this share.
    baseline_weight = 1.0 / n_total

    # Build raw dict before renormalisation
    raw: Dict[str, float] = {}
    for name in unreliable:
        raw[name] = baseline_weight
    unreliable_total = baseline_weight * len(unreliable)

    # Scale reliable weights to fill the remaining probability mass
    remaining_mass = 1.0 - unreliable_total
    for name, w in zip(reliable_names, reliable_weights):
        raw[name] = w * remaining_mass

    # Normalise to ensure sum = 1.0 exactly (float rounding guard)
    total = sum(raw.values())
    weights = {name: round(raw[name] / total, 6) for name in strategy_names}

    return weights


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive strategy weights from prediction backtest results."
    )
    parser.add_argument(
        "--horizon", type=int, default=30,
        help="Target horizon in days to derive weights for (default: 30).",
    )
    parser.add_argument(
        "--all-horizons", action="store_true",
        help="Aggregate all summary files regardless of horizon.",
    )
    parser.add_argument(
        "--min-samples", type=int, default=MIN_SAMPLES,
        help=f"Minimum directional signals before trusting accuracy (default: {MIN_SAMPLES}).",
    )
    parser.add_argument(
        "--temperature", type=float, default=SOFTMAX_TEMPERATURE,
        help=f"Softmax temperature for weight smoothing (default: {SOFTMAX_TEMPERATURE}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print weights but do not write to disk.",
    )
    args = parser.parse_args()

    pred_dir = Path(paths.PRED_BACKTEST)
    print(f"\nSearching for backtest summaries in: {pred_dir}")
    summary_files = _find_summary_files(pred_dir)
    print(f"Found {len(summary_files)} summary file(s).\n")

    if not summary_files:
        print("Error: No prediction_backtest_summary.json files found.")
        print(f"Run the prediction backtest first:  python scripts/workstreams/run_workstreams.py --workstream b")
        sys.exit(1)

    target_horizon = None if args.all_horizons else args.horizon
    horizon_label = "all" if args.all_horizons else str(args.horizon)
    print(f"Horizon filter: {horizon_label} days")
    print(f"Min-sample floor: {args.min_samples}")
    print(f"Softmax temperature: {args.temperature}\n")

    aggregated, n_used = _aggregate_accuracy(summary_files, target_horizon)

    if n_used == 0:
        print(f"Error: No summary files matched horizon={args.horizon}.")
        print("Available horizons in found summaries:")
        for p in summary_files:
            d = _load_summary(p)
            if d:
                print(f"  {p}  →  horizon_days={d.get('horizon_days', 'unknown')}")
        print("\nRe-run with --all-horizons to ignore the horizon filter.")
        sys.exit(1)

    print(f"Aggregated from {n_used} summary file(s):\n")
    new_weights = derive_weights(
        aggregated,
        _ALL_STRATEGY_NAMES,
        min_samples=args.min_samples,
        temperature=args.temperature,
        verbose=True,
    )

    print(f"\nDerived weights (horizon={horizon_label}):")
    print(f"  {'Strategy':<40} {'Weight':>8}  {'Prev hardcoded':>14}")
    _PREV = {
        "Supertrend":                     0.18,
        "MACD + RSI":                     0.15,
        "Ichimoku Cloud":                 0.14,
        "EMA Crossover":                  0.12,
        "S/R Breakout":                   0.12,
        "Bollinger Squeeze":              0.10,
        "RSI Divergence":                 0.08,
        "OBV Divergence":                 0.07,
        "Mean Reversion":                 0.04,
        "ML Meta-Learner (XGBoost proxy)": None,
    }
    for name, w in sorted(new_weights.items(), key=lambda x: -x[1]):
        prev = _PREV.get(name)
        prev_str = f"{prev:.3f}" if prev is not None else "  —   "
        print(f"  {name:<40} {w:>8.6f}  {prev_str:>14}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    # Load existing weights file (to preserve other horizons)
    existing: Dict = {}
    if _WEIGHTS_FILE.exists():
        try:
            existing = json.loads(_WEIGHTS_FILE.read_text())
        except Exception:
            existing = {}

    key = horizon_label
    existing[key] = new_weights

    _WEIGHTS_FILE.write_text(json.dumps(existing, indent=2))
    print(f"\n✓ Weights written → {_WEIGHTS_FILE}")
    print(f"  Key: '{key}'  ({len(new_weights)} strategies)")


if __name__ == "__main__":
    main()
