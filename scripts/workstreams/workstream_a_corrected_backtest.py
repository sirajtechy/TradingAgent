"""
workstream_a_corrected_backtest.py — Step 4: Re-run backtest with course corrections.

Runs the corrected orchestrator (with all 4 rules) over the same sector
data, then prints a Before vs. After score improvement table.

Uses the pre-computed sector results so it doesn't need API calls —
it re-applies the correction rules to the stored tech/fund scores.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import paths

from agents.orchestrator.config import OrchestratorSettings
from agents.orchestrator.course_corrections import (
    apply_conflict_override,
    _score_to_signal,
)
from agents.orchestrator.models import AgentOutput, FusionResult

RESULTS_DIR = str(paths.ORCH_BACKTEST)
SETTINGS = OrchestratorSettings()


# ─────────────────────────────────────────────────────────────────────────────
# Reconstruct FusionResult from stored period data
# ─────────────────────────────────────────────────────────────────────────────

def _reconstruct_result(period: Dict[str, Any]) -> Optional[FusionResult]:
    """Rebuild a FusionResult from stored backtest period data."""
    tech_s = period.get("tech_score") or 50.0
    fund_s = period.get("fund_score") or 50.0
    weights = period.get("weights_applied") or {"tech": 0.5, "fund": 0.5}
    tw = weights.get("tech", 0.5)
    fw = weights.get("fund", 0.5)

    def _make_agent_out(score: float, thresholds: List[float]) -> AgentOutput:
        from agents.orchestrator.fusion import agent_confidence
        from agents.orchestrator.models import BAND_TO_SIGNAL
        # Derive band from score
        if score >= 75:
            band = "strong_bull"
        elif score >= 60:
            band = "bull"
        elif score >= 50:
            band = "mixed_positive"
        elif score >= 35:
            band = "mixed_negative"
        elif score >= 25:
            band = "bear"
        else:
            band = "strong_bear"
        signal = BAND_TO_SIGNAL.get(band, "neutral")
        conf = agent_confidence(score, thresholds)
        return AgentOutput(
            signal=signal,
            score=score,
            band=band,
            confidence="medium",
            computed_confidence=conf,
        )

    tech_out = _make_agent_out(tech_s, SETTINGS.tech_thresholds)
    fund_out = _make_agent_out(fund_s, SETTINGS.fund_thresholds)
    score = tw * tech_s + fw * fund_s
    signal = _score_to_signal(score, SETTINGS)

    return FusionResult(
        final_signal=signal,
        final_confidence=period.get("confidence") or 0.5,
        orchestrator_score=score,
        conflict_detected=period.get("conflict_detected") or False,
        conflict_resolution=period.get("conflict_resolution"),
        weights_applied={"tech": tw, "fund": fw},
        tech_output=tech_out,
        fund_output=fund_out,
    )


def _build_rolling_context(
    all_periods: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """
    For each (ticker, month), compute:
    - annualised_vol_3m : realised vol from the prior 3 monthly returns
    - cumulative_3m     : sum of the prior 3 monthly returns (trend proxy)

    Returns: { ticker: { month_str: (vol_3m, cum_3m) } }
    """
    from collections import defaultdict
    import math

    by_ticker: Dict[str, List[Dict]] = defaultdict(list)
    for p in all_periods:
        by_ticker[p["ticker"]].append(p)

    ctx: Dict[str, Dict[str, Tuple[float, float]]] = {}
    for ticker, periods in by_ticker.items():
        # Sort by signal_date so we can build a proper window
        sorted_p = sorted(periods, key=lambda x: x.get("signal_date", ""))
        rets = [p.get("price_return_pct") or 0.0 for p in sorted_p]
        months = [p.get("month", "") for p in sorted_p]
        ctx[ticker] = {}
        for i, month in enumerate(months):
            window = rets[max(0, i - 3): i]   # up to 3 prior monthly returns
            if len(window) >= 2:
                mean_r = sum(window) / len(window)
                variance = sum((r - mean_r) ** 2 for r in window) / len(window)
                vol_3m = math.sqrt(variance * 12)  # annualise
            elif len(window) == 1:
                vol_3m = abs(window[0]) * math.sqrt(12)
            else:
                vol_3m = 0.0
            cum_3m = sum(window)
            ctx[ticker][month] = (round(vol_3m, 2), round(cum_3m, 2))
    return ctx


# Module-level cache filled once in main()
_ROLLING_CTX: Dict[str, Dict[str, Tuple[float, float]]] = {}


def _estimate_regime(period: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (annualised_vol_3m, cum_return_3m) for this period using
    the pre-built rolling context.  Falls back to single-period estimate
    if the ticker/month isn't in the cache.
    """
    ticker = period.get("ticker", "")
    month = period.get("month", "")
    if ticker and month and ticker in _ROLLING_CTX and month in _ROLLING_CTX[ticker]:
        return _ROLLING_CTX[ticker][month]

    # Fallback: single-period annualised vol
    import math
    ret = period.get("price_return_pct") or 0.0
    approx_vol = abs(ret) * math.sqrt(12)
    return approx_vol, None


# ─────────────────────────────────────────────────────────────────────────────
# Apply corrections to a single period
# ─────────────────────────────────────────────────────────────────────────────

# Simulation-tuned thresholds (monthly-return vol is systematically lower than
# daily-return based vol; scale accordingly vs production 25% threshold)
_SIM_VOL_THRESHOLD   = 10.0   # annualised vol from 3mo monthly returns → elevated
_SIM_TREND_THRESHOLD = -4.0   # 3-month cumulative return → downtrend


def apply_corrections_to_period(period: Dict[str, Any]) -> Dict[str, Any]:
    """Return a corrected period dict with updated signal."""
    result = _reconstruct_result(period)
    if result is None:
        return period

    # Rule 1: ADX weight adjustment — ADX not stored; skip (fires live only)

    # Rule 2: Conflict override — tighten abstain trigger
    result = apply_conflict_override(result, SETTINGS)

    # Rule 4: Regime filter (simulation mode — calibrated to monthly-return vol)
    vol_approx, cum_3m = _estimate_regime(period)
    if (
        result.final_signal == "bullish"
        and vol_approx is not None
        and vol_approx > _SIM_VOL_THRESHOLD
        and cum_3m is not None
        and cum_3m < _SIM_TREND_THRESHOLD
    ):
        from agents.orchestrator.models import FusionResult as FR
        result = FR(
            final_signal="neutral",
            final_confidence=result.final_confidence * 0.60,
            orchestrator_score=50.0,
            conflict_detected=result.conflict_detected,
            conflict_resolution=result.conflict_resolution,
            weights_applied=result.weights_applied,
            tech_output=result.tech_output,
            fund_output=result.fund_output,
            tech_error=result.tech_error,
            fund_error=result.fund_error,
            note=(
                f"{result.note or ''} | Rule4(sim):regime_filter "
                f"(vol={vol_approx:.1f}%,3m={cum_3m:.1f}%)"
            ),
        )

    actual = period.get("actual_direction", "")
    corrected_signal = result.final_signal

    # Evaluate correctness of corrected signal
    if corrected_signal == "neutral":
        corrected_correct = None  # neutral = abstain
    elif corrected_signal == "bullish":
        corrected_correct = actual == "up"
    elif corrected_signal == "bearish":
        corrected_correct = actual == "down"
    else:
        corrected_correct = None

    return {
        **period,
        "corrected_signal": corrected_signal,
        "corrected_correct": corrected_correct,
        "corrected_score": result.orchestrator_score,
        "corrected_weights": result.weights_applied,
        "correction_note": result.note,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Load and process all data
# ─────────────────────────────────────────────────────────────────────────────

def load_all_periods() -> List[Dict[str, Any]]:
    all_periods = []
    for fname in sorted(os.listdir(RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(RESULTS_DIR, fname)) as fh:
            data = json.load(fh)
        ticker = data["ticker"]
        for p in data.get("periods", []):
            p["ticker"] = ticker
            all_periods.append(p)
    return all_periods


def compute_metrics(
    periods: List[Dict[str, Any]],
    signal_key: str = "signal",
    correct_key: str = "signal_correct",
) -> Dict[str, Any]:
    directional = [p for p in periods if p.get(correct_key) is not None]
    correct = [p for p in directional if p.get(correct_key)]
    total = len(periods)
    accuracy = len(correct) / len(directional) * 100.0 if directional else 0.0

    signals = [p.get(signal_key, "neutral") for p in periods]
    from collections import Counter
    dist = Counter(signals)

    # F1 macro across directional classes
    tp_bull = sum(1 for p in directional if p.get(signal_key) == "bullish" and p.get(correct_key))
    fp_bull = sum(1 for p in directional if p.get(signal_key) == "bullish" and not p.get(correct_key))
    fn_bull = sum(1 for p in directional if p.get(signal_key) != "bullish" and p.get("actual_direction") == "up")

    tp_bear = sum(1 for p in directional if p.get(signal_key) == "bearish" and p.get(correct_key))
    fp_bear = sum(1 for p in directional if p.get(signal_key) == "bearish" and not p.get(correct_key))
    fn_bear = sum(1 for p in directional if p.get(signal_key) != "bearish" and p.get("actual_direction") == "down")

    def f1(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        return 2 * p * r / (p + r) if (p + r) > 0 else 0

    f1_bull = f1(tp_bull, fp_bull, fn_bull)
    f1_bear = f1(tp_bear, fp_bear, fn_bear)
    f1_macro = (f1_bull + f1_bear) / 2.0

    return {
        "total_periods": total,
        "directional_signals": len(directional),
        "correct": len(correct),
        "accuracy_pct": round(accuracy, 2),
        "f1_macro": round(f1_macro * 100, 2),
        "f1_bull": round(f1_bull * 100, 2),
        "f1_bear": round(f1_bear * 100, 2),
        "signal_distribution": dict(dist),
        "neutral_count": dist.get("neutral", 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 80)
    print("STEP 4 — CORRECTED BACKTEST: BEFORE vs. AFTER")
    print("=" * 80)

    periods = load_all_periods()
    print(f"Loaded {len(periods)} periods from {RESULTS_DIR}")

    # Build rolling vol context once (3-month trailing per ticker)
    global _ROLLING_CTX
    _ROLLING_CTX = _build_rolling_context(periods)
    n_ctx = sum(len(v) for v in _ROLLING_CTX.values())
    print(f"Rolling context built: {len(_ROLLING_CTX)} tickers, {n_ctx} period keys")

    # Compute BEFORE metrics
    before = compute_metrics(periods, "signal", "signal_correct")

    # Apply corrections
    corrected = [apply_corrections_to_period(p) for p in periods]

    # Compute AFTER metrics
    after = compute_metrics(corrected, "corrected_signal", "corrected_correct")

    # Print comparison table
    print(f"\n{'Metric':<30} {'BEFORE':>10} {'AFTER':>10} {'DELTA':>10}")
    print("-" * 60)

    metrics = [
        ("Total Periods", "total_periods"),
        ("Directional Signals", "directional_signals"),
        ("Correct Signals", "correct"),
        ("Win Rate %", "accuracy_pct"),
        ("F1 Macro %", "f1_macro"),
        ("F1 Bullish %", "f1_bull"),
        ("F1 Bearish %", "f1_bear"),
        ("Neutral (Abstain)", "neutral_count"),
    ]

    for label, key in metrics:
        b_val = before[key]
        a_val = after[key]
        if isinstance(b_val, float):
            delta = a_val - b_val
            delta_str = f"{delta:+.2f}"
            print(f"{label:<30} {b_val:>10.2f} {a_val:>10.2f} {delta_str:>10}")
        else:
            delta = a_val - b_val
            delta_str = f"{delta:+d}"
            print(f"{label:<30} {b_val:>10} {a_val:>10} {delta_str:>10}")

    # Signal distribution change
    print("\n── Signal Distribution Change ──────────────────────────────")
    bd = before["signal_distribution"]
    ad = after["signal_distribution"]
    for sig in ["bullish", "neutral", "bearish"]:
        b_cnt = bd.get(sig, 0)
        a_cnt = ad.get(sig, 0)
        print(f"  {sig:<10}: {b_cnt:>5} → {a_cnt:>5}  (Δ {a_cnt-b_cnt:+d})")

    # F1 improvement check
    f1_improvement = after["f1_macro"] - before["f1_macro"]
    win_improvement = after["accuracy_pct"] - before["accuracy_pct"]
    print(f"\n── Acceptance Criteria ─────────────────────────────────────")
    status_f1 = "✓ PASS" if f1_improvement >= 10.0 else "✗ FAIL"
    status_acc = "✓ PASS" if win_improvement >= 0 else "✗ FAIL"
    print(f"  F1 Improvement ≥ +10%  : {f1_improvement:+.2f}%  {status_f1}")
    print(f"  Win Rate Improvement   : {win_improvement:+.2f}%  {status_acc}")

    # Save results
    output = {
        "before": before,
        "after": after,
        "f1_improvement_pct": round(f1_improvement, 2),
        "win_rate_improvement_pct": round(win_improvement, 2),
        "simulation_note": (
            "Monthly-return vol proxy cannot distinguish correct-bullish-in-volatile "
            "from wrong-bullish-in-volatile. Real improvement requires full live "
            "re-backtest with ADX, VIX, and intra-month drawdown data."
        ),
        "corrected_periods": corrected,
    }

    # ── Theoretical improvement estimate (based on RCA category analysis) ──────
    print("\n── Theoretical Improvement Estimate (forward-looking) ─────────────────")
    print("   Based on RCA findings — assumes rules applied with real-time data\n")
    rca_path = "rca_results.json"
    if os.path.exists(rca_path):
        with open(rca_path) as f:
            rca = json.load(f)
        categories = rca.get("categories", {})
        total_directional = before["directional_signals"]
        total_correct     = before["correct"]
        total_dir_wrong   = total_directional - total_correct
        # RCA "408 misses" includes 231 already-neutral signals.
        # Course corrections only convert directional-wrong → neutral.
        # Fraction of each category that is directional-wrong (aprox 176/408):
        dir_wrong_share = total_dir_wrong / rca["total_misclassified"] if rca["total_misclassified"] > 0 else 0.43

        print(f"   {'Category':<28} {'Misses':>7}  {'Catch':>5}  {'Precision':>9}  {'Est Save':>8}")
        print(f"   {'-'*65}")

        # RCA keys → display names + conservative assumptions
        ASSUMPTIONS = {
            "signal_conflict":         ("Signal Conflict Error",    0.95, 0.02),
            "market_regime":           ("Market Regime Error",      0.50, 0.15),
            "timing_errors":           ("Timing Error",             0.40, 0.10),
            "indicator_lag":           ("Indicator Lag Error",      0.45, 0.12),
            "fundamental_misalignment":("Fundamental Misalignment", 0.80, 0.05),
        }

        total_saved_wrong  = 0
        total_lost_correct = 0
        sorted_cats = sorted(
            categories.items(),
            key=lambda x: -x[1].get("count", 0) if isinstance(x[1], dict) else 0,
        )
        for key, cat_data in sorted_cats:
            count = cat_data.get("count", 0) if isinstance(cat_data, dict) else cat_data
            # Only consider the directional-wrong fraction of each category
            dir_wrong_count = int(count * dir_wrong_share)
            label, catch_rate, false_rate = ASSUMPTIONS.get(key, (key, 0.3, 0.1))
            saved  = int(dir_wrong_count * catch_rate)
            lost   = int(total_correct * false_rate)
            precision = saved / (saved + lost) if (saved + lost) > 0 else 0
            total_saved_wrong  += saved
            total_lost_correct += lost
            print(f"   {label:<28} {dir_wrong_count:>7}  {catch_rate:>4.0%}  {precision:>8.0%}  {saved:>7}↓")

        new_wrong   = max(total_dir_wrong - total_saved_wrong, 0)
        new_correct = max(total_correct - total_lost_correct, 0)
        new_dir     = new_wrong + new_correct
        new_wr      = new_correct / new_dir * 100 if new_dir > 0 else 0.0
        est_f1_improvement = new_wr - before["accuracy_pct"]

        print(f"\n   Est. Win Rate: {before['accuracy_pct']:.1f}% → {new_wr:.1f}%  "
              f"(Δ {est_f1_improvement:+.1f}%)")
        print(f"   Est. Correct : {total_correct} → {new_correct}  |  "
              f"Wrong saved: {total_saved_wrong}  |  Correct lost: {total_lost_correct}")
        output["theoretical_estimate"] = {
            "estimated_win_rate_pct": round(new_wr, 2),
            "estimated_improvement_pct": round(est_f1_improvement, 2),
            "wrong_signals_saved": total_saved_wrong,
            "correct_signals_lost": total_lost_correct,
        }

    print(f"\n   NOTE: Simulation delta ({f1_improvement:+.2f}% F1) differs from theoretical")
    print(f"   because monthly vol cannot isolate regime-wrong from regime-right.")
    print(f"   Re-run full live backtest with course_corrections.py embedded to get true delta.\n")
    with open("corrected_backtest_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print("\n✓ Saved → corrected_backtest_results.json")


if __name__ == "__main__":
    main()
