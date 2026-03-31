#!/usr/bin/env python3
"""
Misclassification Audit — Fundamental Agent (v2 scoring)

Reads sector_backtest_results.json and traces every wrong prediction back to
the specific framework(s) that caused the error.  Produces:
  1. Summary statistics (FP vs FN breakdown)
  2. Root-cause frequency table
  3. Framework fault-frequency table
  4. Per-subscore analysis (which weighted bucket drove the error)
  5. Line-by-line detail with root-cause annotation
  6. JSON export for downstream analysis
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RESULTS_FILE = Path("sector_backtest_results.json")

# ── v2 scoring weights (must match rules.py) ──────────────────────────────
WEIGHTS = {
    "financial_health": 0.25,   # avg(piotroski, altman)
    "valuation":        0.30,   # avg(graham, lynch)
    "quality":          0.25,   # greenblatt
    "growth":           0.20,   # growth_profile
}

# Framework → subscore mapping
SUBSCORE_MAP = {
    "piotroski":      "financial_health",
    "altman":         "financial_health",
    "graham":         "valuation",
    "lynch":          "valuation",
    "greenblatt":     "quality",
    "growth_profile": "growth",
}

# Per-framework thresholds for fault classification
BULL_THRESH = 60   # score_pct >= 60 → bullish contributor
BEAR_THRESH = 40   # score_pct < 40  → bearish contributor


# ── Helpers ────────────────────────────────────────────────────────────────

def reconstruct_subscores(fws: Dict[str, Any]) -> Dict[str, float | None]:
    """Rebuild the 4 weighted subscores from individual frameworks."""
    buckets: Dict[str, List[float]] = {
        "financial_health": [],
        "valuation": [],
        "quality": [],
        "growth": [],
    }
    for fw_name, bucket_name in SUBSCORE_MAP.items():
        vals = fws.get(fw_name, {})
        if vals.get("applicable") and vals.get("score_pct") is not None:
            buckets[bucket_name].append(vals["score_pct"])

    return {
        k: (sum(v) / len(v) if v else None)
        for k, v in buckets.items()
    }


def classify_framework(score_pct: float | None, applicable: bool) -> str:
    if score_pct is None or not applicable:
        return "N/A"
    if score_pct >= BULL_THRESH:
        return "bullish"
    if score_pct < BEAR_THRESH:
        return "bearish"
    return "neutral"


def identify_root_causes(
    signal: str,
    fws: Dict[str, Any],
    subscores: Dict[str, float | None],
    composite: float | None,
) -> Tuple[List[str], str]:
    """
    Determine root cause(s) of a misclassification.
    Returns (list_of_root_causes, primary_category).
    """
    causes: List[str] = []
    category = "unknown"

    # Classify each framework
    fw_classes = {}
    for name, vals in fws.items():
        if name == "shariah":
            continue
        fw_classes[name] = classify_framework(
            vals.get("score_pct"), vals.get("applicable", False)
        )

    if signal == "bullish":
        # FALSE POSITIVE: predicted UP, went DOWN
        bull_fws = [k for k, v in fw_classes.items() if v == "bullish"]
        bear_fws = [k for k, v in fw_classes.items() if v == "bearish"]
        na_fws   = [k for k, v in fw_classes.items() if v == "N/A"]

        # Category 1: Healthy but overvalued
        health = subscores.get("financial_health")
        valuation = subscores.get("valuation")
        if health and valuation and health >= 65 and valuation < 50:
            causes.append(
                f"Healthy but overvalued: financial_health={health:.1f} vs valuation={valuation:.1f}"
            )
            category = "healthy_but_overvalued"

        # Category 2: High Piotroski / Altman inflated health score
        pio = fws.get("piotroski", {}).get("score_pct")
        alt = fws.get("altman", {}).get("score_pct")
        if pio and pio >= 75:
            causes.append(f"Piotroski inflated health ({pio:.1f}%) — backward-looking metric")
        if alt and alt >= 65:
            causes.append(f"Altman Z in safe zone ({alt:.1f}%) — doesn't predict sudden drops")

        # Category 3: Lynch N/A → valuation subscore undersampled
        if "lynch" in na_fws:
            causes.append("Lynch N/A → valuation subscore based on Graham alone (undersampled)")
            if category == "unknown":
                category = "missing_indicator"

        # Category 4: Growth looked strong but price already priced it in
        gp = fws.get("growth_profile", {}).get("score_pct")
        if gp and gp >= 60:
            causes.append(f"Growth profile bullish ({gp:.1f}%) — growth may be priced in")

        # Category 5: Borderline score barely crossed threshold
        if composite and 62 <= composite < 66:
            causes.append(f"Borderline bullish (score={composite:.1f}, threshold=62)")
            if category == "unknown":
                category = "borderline_call"

        # Category 6: Bearish signals were outvoted
        if bear_fws:
            scores_str = ", ".join(
                f"{k}={fws[k]['score_pct']:.1f}%" for k in bear_fws
                if fws[k].get("score_pct") is not None
            )
            causes.append(f"Bearish signals outvoted: {scores_str}")
            if category == "unknown":
                category = "conflicting_outvoted"

        # Category 7: Greenblatt quality was middling but counted as positive
        gb = fws.get("greenblatt", {}).get("score_pct")
        if gb and 50 <= gb < 65:
            causes.append(f"Greenblatt middling ({gb:.1f}%) — not clearly bullish but above midpoint")

        if not causes:
            causes.append("All frameworks aligned bullish — no single indicator fault, likely macro/sentiment")
            category = "macro_blind_spot"

    elif signal == "bearish":
        # FALSE NEGATIVE: predicted DOWN, went UP
        bull_fws = [k for k, v in fw_classes.items() if v == "bullish"]

        # Which frameworks dragged the score below 40?
        low_fws = {
            k: fws[k]["score_pct"]
            for k, v in fw_classes.items()
            if v == "bearish" and fws[k].get("score_pct") is not None
        }
        if low_fws:
            scores_str = ", ".join(f"{k}={v:.1f}%" for k, v in low_fws.items())
            causes.append(f"Bearish frameworks dragged score down: {scores_str}")

        # Graham often fails strong-growth tech stocks
        gr = fws.get("graham", {}).get("score_pct")
        if gr is not None and gr < 30:
            causes.append(f"Graham too strict ({gr:.1f}%) — penalises growth stocks with no dividend / high P/E")
            category = "graham_too_strict"

        # Bull signals were ignored
        if bull_fws:
            scores_str = ", ".join(
                f"{k}={fws[k]['score_pct']:.1f}%" for k in bull_fws
                if fws[k].get("score_pct") is not None
            )
            causes.append(f"Bullish signals overridden: {scores_str}")
            if category == "unknown":
                category = "conflicting_outvoted"

        if not causes:
            causes.append("All frameworks aligned bearish — stock rallied against fundamentals")
            category = "fundamental_disconnect"

    if category == "unknown":
        category = "multiple_factors"

    return causes, category


# ── Main audit ─────────────────────────────────────────────────────────────

def run_audit() -> List[Dict[str, Any]]:
    with open(RESULTS_FILE) as f:
        data = json.load(f)

    all_misses: List[Dict[str, Any]] = []

    for sector_name, sector_data in data["sectors"].items():
        for ticker, ticker_data in sector_data["tickers"].items():
            if not ticker_data or not ticker_data.get("periods"):
                continue
            for p in ticker_data["periods"]:
                if p.get("signal_correct") is not False:
                    continue

                signal = p["signal"]
                actual = p["actual_direction"]
                fws    = p.get("frameworks", {})
                composite = p.get("experimental_score")

                subscores = reconstruct_subscores(fws)
                causes, category = identify_root_causes(signal, fws, subscores, composite)

                # Frameworks that pushed in the WRONG direction
                if signal == "bullish":
                    at_fault = {
                        k: fws[k]["score_pct"]
                        for k in SUBSCORE_MAP
                        if classify_framework(
                            fws.get(k, {}).get("score_pct"),
                            fws.get(k, {}).get("applicable", False),
                        ) == "bullish"
                    }
                    error_type = "FP"
                elif signal == "bearish":
                    at_fault = {
                        k: fws[k]["score_pct"]
                        for k in SUBSCORE_MAP
                        if classify_framework(
                            fws.get(k, {}).get("score_pct"),
                            fws.get(k, {}).get("applicable", False),
                        ) == "bearish"
                    }
                    error_type = "FN"
                else:
                    continue

                all_misses.append({
                    "ticker": ticker,
                    "sector": sector_name,
                    "month": p["month"],
                    "signal_date": p["signal_date"],
                    "predicted": signal.upper(),
                    "actual": actual.upper(),
                    "return_pct": p["price_return_pct"],
                    "composite_score": composite,
                    "band": p["score_band"],
                    "error_type": error_type,
                    "subscores": {k: round(v, 1) if v else None for k, v in subscores.items()},
                    "frameworks_at_fault": at_fault,
                    "all_framework_scores": {
                        k: fws.get(k, {}).get("score_pct") for k in SUBSCORE_MAP
                    },
                    "root_causes": causes,
                    "category": category,
                    "data_quality": p.get("data_quality", {}),
                })

    return all_misses


def print_report(all_misses: List[Dict[str, Any]]):
    total_periods = 0
    with open(RESULTS_FILE) as f:
        data = json.load(f)
    for s in data["sectors"].values():
        for t in s["tickers"].values():
            if t and t.get("periods"):
                total_periods += len(t["periods"])

    n_tickers = sum(len(s["tickers"]) for s in data["sectors"].values())

    print(f"\n{'='*100}")
    print(f"  FUNDAMENTAL AGENT — MISCLASSIFICATION AUDIT (v2 scoring)")
    print(f"  {len(all_misses)} errors out of {total_periods} total periods "
          f"across {n_tickers} tickers")
    print(f"{'='*100}\n")

    fp = [m for m in all_misses if m["error_type"] == "FP"]
    fn = [m for m in all_misses if m["error_type"] == "FN"]
    print(f"  False Positives (predicted BULLISH, went DOWN): {len(fp)}")
    print(f"  False Negatives (predicted BEARISH, went UP):   {len(fn)}\n")

    # ── 1. Category breakdown ──────────────────────────────────────────────
    cat_freq: Dict[str, int] = {}
    for m in all_misses:
        cat_freq[m["category"]] = cat_freq.get(m["category"], 0) + 1

    print("─" * 100)
    print("  ROOT CAUSE CATEGORIES")
    print("─" * 100)
    for cat, count in sorted(cat_freq.items(), key=lambda x: -x[1]):
        pct = count / len(all_misses) * 100
        label = {
            "healthy_but_overvalued":  "Healthy but overvalued (strong health, weak valuation)",
            "missing_indicator":       "Missing indicator (Lynch N/A → undersampled valuation)",
            "borderline_call":         "Borderline bullish (score 62-66, barely crossed threshold)",
            "conflicting_outvoted":    "Conflicting signals resolved incorrectly",
            "macro_blind_spot":        "Macro/sentiment blind spot (all frameworks agreed, still wrong)",
            "graham_too_strict":       "Graham too strict for growth stocks",
            "fundamental_disconnect":  "Stock rallied against weak fundamentals",
            "multiple_factors":        "Multiple contributing factors",
        }.get(cat, cat)
        print(f"  {count:>3}× ({pct:4.1f}%)  {label}")

    # ── 2. Framework fault frequency ───────────────────────────────────────
    fault_freq: Dict[str, int] = {}
    for m in all_misses:
        for fw in m["frameworks_at_fault"]:
            fault_freq[fw] = fault_freq.get(fw, 0) + 1

    print(f"\n{'─'*100}")
    print("  FRAMEWORK FAULT FREQUENCY (pushed score in the wrong direction)")
    print("─" * 100)
    for fw, count in sorted(fault_freq.items(), key=lambda x: -x[1]):
        pct = count / len(all_misses) * 100
        subscore = SUBSCORE_MAP.get(fw, "?")
        print(f"  {count:>3}× ({pct:4.1f}%)  {fw:<16} [subscore: {subscore}, weight: {WEIGHTS.get(subscore, '?')}]")

    # ── 3. Subscore-level analysis ─────────────────────────────────────────
    print(f"\n{'─'*100}")
    print("  SUBSCORE ANALYSIS — Average values for misclassified vs all periods")
    print("─" * 100)

    # Compute average subscores for misclassified periods
    sub_sums: Dict[str, List[float]] = {k: [] for k in WEIGHTS}
    for m in all_misses:
        for k, v in m["subscores"].items():
            if v is not None:
                sub_sums[k].append(v)

    for sub_name in WEIGHTS:
        vals = sub_sums[sub_name]
        if vals:
            avg_val = sum(vals) / len(vals)
            print(f"  {sub_name:<20}  avg={avg_val:5.1f}  weight={WEIGHTS[sub_name]}  "
                  f"(n={len(vals)} misclassifications)")

    # ── 4. FP detail — by sector ───────────────────────────────────────────
    if fp:
        print(f"\n{'='*100}")
        print(f"  FALSE POSITIVES — {len(fp)} cases (predicted BULLISH, went DOWN)")
        print(f"{'='*100}")

        fp_by_sector: Dict[str, List] = {}
        for m in fp:
            fp_by_sector.setdefault(m["sector"], []).append(m)

        for sector in sorted(fp_by_sector):
            items = sorted(fp_by_sector[sector], key=lambda x: (x["ticker"], x["signal_date"]))
            print(f"\n  ┌─ {sector} ({len(items)} FP)")
            print(f"  │ {'STOCK':<7} {'MONTH':<14} {'RET%':>7} {'SCORE':>6} "
                  f"{'HLTH':>5} {'VALN':>5} {'QUAL':>5} {'GRWT':>5}  CATEGORY")
            print(f"  │ {'─'*85}")
            for m in items:
                ss = m["subscores"]
                h = f"{ss['financial_health']:.0f}" if ss['financial_health'] else " - "
                v = f"{ss['valuation']:.0f}" if ss['valuation'] else " - "
                q = f"{ss['quality']:.0f}" if ss['quality'] else " - "
                g = f"{ss['growth']:.0f}" if ss['growth'] else " - "
                print(f"  │ {m['ticker']:<7} {m['month']:<14} {m['return_pct']:>+6.1f}% "
                      f"{m['composite_score']:>5.1f}  {h:>5} {v:>5} {q:>5} {g:>5}  {m['category']}")
                for rc in m["root_causes"]:
                    print(f"  │          └─ {rc}")
            print(f"  └{'─'*95}")

    # ── 5. FN detail — by sector ───────────────────────────────────────────
    if fn:
        print(f"\n{'='*100}")
        print(f"  FALSE NEGATIVES — {len(fn)} cases (predicted BEARISH, went UP)")
        print(f"{'='*100}")

        fn_by_sector: Dict[str, List] = {}
        for m in fn:
            fn_by_sector.setdefault(m["sector"], []).append(m)

        for sector in sorted(fn_by_sector):
            items = sorted(fn_by_sector[sector], key=lambda x: (x["ticker"], x["signal_date"]))
            print(f"\n  ┌─ {sector} ({len(items)} FN)")
            print(f"  │ {'STOCK':<7} {'MONTH':<14} {'RET%':>7} {'SCORE':>6} "
                  f"{'HLTH':>5} {'VALN':>5} {'QUAL':>5} {'GRWT':>5}  CATEGORY")
            print(f"  │ {'─'*85}")
            for m in items:
                ss = m["subscores"]
                h = f"{ss['financial_health']:.0f}" if ss['financial_health'] else " - "
                v = f"{ss['valuation']:.0f}" if ss['valuation'] else " - "
                q = f"{ss['quality']:.0f}" if ss['quality'] else " - "
                g = f"{ss['growth']:.0f}" if ss['growth'] else " - "
                print(f"  │ {m['ticker']:<7} {m['month']:<14} {m['return_pct']:>+6.1f}% "
                      f"{m['composite_score']:>5.1f}  {h:>5} {v:>5} {q:>5} {g:>5}  {m['category']}")
                for rc in m["root_causes"]:
                    print(f"  │          └─ {rc}")
            print(f"  └{'─'*95}")

    # ── 6. Worst offenders (tickers with most errors) ──────────────────────
    print(f"\n{'─'*100}")
    print("  WORST OFFENDERS — Tickers with most misclassifications")
    print("─" * 100)
    ticker_counts: Dict[str, Dict[str, int]] = {}
    for m in all_misses:
        key = m["ticker"]
        if key not in ticker_counts:
            ticker_counts[key] = {"FP": 0, "FN": 0, "total": 0, "sector": m["sector"]}
        ticker_counts[key][m["error_type"]] += 1
        ticker_counts[key]["total"] += 1

    for ticker, counts in sorted(ticker_counts.items(), key=lambda x: -x[1]["total"])[:15]:
        print(f"  {ticker:<7} [{counts['sector']:<22}]  "
              f"FP={counts['FP']}  FN={counts['FN']}  total={counts['total']}")


def main():
    if not RESULTS_FILE.exists():
        print(f"ERROR: {RESULTS_FILE} not found. Run the sector backtest first.")
        return

    all_misses = run_audit()
    print_report(all_misses)

    # Save JSON
    out_path = Path("misclassification_audit.json")
    with open(out_path, "w") as f:
        json.dump(all_misses, f, indent=2, default=str)
    print(f"\n✓  Full audit saved to {out_path}  ({len(all_misses)} records)")


if __name__ == "__main__":
    main()
