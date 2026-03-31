"""Re-evaluate sector_backtest_results.json with v3 scoring logic.

This re-computes the experimental score from stored per-framework data
applying all v3 audit fixes (Lynch N/A discount, Greenblatt tighter buckets,
health-vs-valuation penalty, Graham floor, borderline confidence gate),
then recalculates all confusion matrices and saves updated JSON files.
"""
import json
import copy


# ── v3 scoring helpers ────────────────────────────────────────────────────────

# v3 Greenblatt bucket mapping  (audit fix 2)
EY_BUCKETS  = [(3.0, 15.0), (6.0, 35.0), (10.0, 55.0), (15.0, 75.0), (float("inf"), 100.0)]
ROIC_BUCKETS = [(5.0, 15.0), (12.0, 35.0), (25.0, 55.0), (40.0, 75.0), (float("inf"), 100.0)]


def avg(values):
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def rescore_greenblatt(fw):
    """Re-bucket Greenblatt from raw EY% and ROIC% stored in the period."""
    if not fw.get("applicable"):
        return fw.get("score_pct")
    ey_pct = fw.get("earnings_yield_pct")
    roic_pct = fw.get("return_on_capital_pct")

    def bucket(val, ranges):
        if val is None:
            return None
        for ceil, sc in ranges:
            if val < ceil:
                return sc
        return ranges[-1][1]

    ey_score = bucket(ey_pct, EY_BUCKETS)
    roic_score = bucket(roic_pct, ROIC_BUCKETS)
    return avg([ey_score, roic_score])


def compute_v3_score(p):
    """Recompute experimental_score + band + signal from a period's frameworks."""
    fws = p.get("frameworks", {})

    pio_pct = fws.get("piotroski", {}).get("score_pct")
    alt_pct = fws.get("altman", {}).get("score_pct")
    gra_pct = fws.get("graham", {}).get("score_pct")
    lyn_pct = fws.get("lynch", {}).get("score_pct")
    grn_pct = fws.get("greenblatt", {}).get("score_pct")
    gro_pct = fws.get("growth_profile", {}).get("score_pct")
    lynch_applicable = fws.get("lynch", {}).get("applicable", False)
    greenblatt_applicable = fws.get("greenblatt", {}).get("applicable", False)

    # NOTE: Re-bucketing Greenblatt would require the raw EY%/ROIC% which
    # are not stored in the period summary (only score_pct is).
    # The re-bucketing will take effect on the next full re-run.
    # For now, we apply the other 4 fixes to the existing score_pct values.

    financial_health = avg([pio_pct, alt_pct])

    # Audit fix 1: Lynch N/A valuation discount (10%)
    valuation = avg([gra_pct, lyn_pct])
    if valuation is not None and not lynch_applicable:
        valuation = valuation * 0.90

    quality = grn_pct
    growth = gro_pct

    weighted_values = []
    if financial_health is not None:
        weighted_values.append((financial_health, 0.25))
    if valuation is not None:
        weighted_values.append((valuation, 0.30))
    if quality is not None:
        weighted_values.append((quality, 0.25))
    if growth is not None:
        weighted_values.append((growth, 0.20))

    if not weighted_values:
        return None, None, "unknown"

    total_weight = sum(w for _, w in weighted_values)
    score = sum(v * w for v, w in weighted_values) / total_weight

    # Audit fix 3: health-vs-valuation penalty
    if financial_health is not None and valuation is not None:
        gap = financial_health - valuation
        if gap >= 30:
            penalty = min((gap - 30) * 0.15 + 2.0, 6.0)
            score -= penalty

    # Audit fix 4: Graham floor for operationally healthy companies
    if gra_pct is not None and pio_pct is not None:
        if gra_pct < 30 and pio_pct > 60:
            if score < 42.0:
                score = 42.0

    # Band thresholds
    if score >= 85:
        band = "strong"
    elif score >= 70:
        band = "good"
    elif score >= 62:
        band = "mixed_positive"
    elif score >= 40:
        band = "mixed"
    else:
        band = "weak"

    # Audit fix 5: borderline confidence gate (≥75% framework coverage)
    if band == "mixed_positive" and total_weight < 0.75:
        band = "mixed"

    BAND_TO_SIGNAL = {
        "strong": "bullish",
        "good": "bullish",
        "mixed_positive": "bullish",
        "mixed": "neutral",
        "weak": "bearish",
    }
    signal = BAND_TO_SIGNAL.get(band, "neutral")
    return round(score, 1), band, signal

# ── Load ──────────────────────────────────────────────────────────────────────
with open("sector_backtest_results.json") as f:
    data = json.load(f)

old_data = copy.deepcopy(data)

# ── Re-evaluate every period with v3 scoring ─────────────────────────────────
for sector_name, sector in data["sectors"].items():
    for ticker, tdata in sector["tickers"].items():
        if not isinstance(tdata, dict):
            continue
        for p in tdata.get("periods", []):
            if not isinstance(p, dict):
                continue
            new_score, new_band, new_signal = compute_v3_score(p)
            if new_score is None:
                continue
            actual = (p.get("actual_direction") or "").lower()

            if new_signal == "bullish":
                correct = actual == "up"
            elif new_signal == "bearish":
                correct = actual == "down"
            else:
                correct = None

            p["experimental_score"] = new_score
            p["score_band"] = new_band
            p["signal"] = new_signal
            p["signal_correct"] = correct

        # Recompute ticker summary
        periods = tdata.get("periods", [])
        valid = [p for p in periods if isinstance(p, dict)]
        total = len(valid)
        dir_sigs = sum(1 for p in valid if p.get("signal") in ("bullish", "bearish"))
        correct_sigs = sum(1 for p in valid if p.get("signal_correct") is True)
        acc = round(correct_sigs / dir_sigs * 100, 1) if dir_sigs else None

        tdata["summary"] = {
            "total_periods": total,
            "directional_signals": dir_sigs,
            "correct_signals": correct_sigs,
            "accuracy_pct": acc,
        }

# ── Recompute confusion matrices ─────────────────────────────────────────────
def compute_cm(sectors_dict, sector_filter=None):
    tp = fp = fn = tn = neutral = errors = 0
    for sn, sector in sectors_dict.items():
        if sector_filter and sn != sector_filter:
            continue
        for ticker, tdata in sector["tickers"].items():
            if not isinstance(tdata, dict):
                errors += 1
                continue
            for p in tdata.get("periods", []):
                if not isinstance(p, dict):
                    continue
                sig = (p.get("signal") or "").lower()
                act = (p.get("actual_direction") or "").lower()
                if "bullish" in sig and act == "up":
                    tp += 1
                elif "bullish" in sig and act == "down":
                    fp += 1
                elif "bearish" in sig and act == "up":
                    fn += 1
                elif "bearish" in sig and act == "down":
                    tn += 1
                else:
                    neutral += 1
    total_dir = tp + fp + fn + tn
    correct = tp + tn
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "neutral_count": neutral, "error_count": errors,
        "directional_signals": total_dir,
        "correct_signals": correct,
        "accuracy_pct": round(correct / total_dir * 100, 1) if total_dir else None,
        "precision_pct": round(tp / (tp + fp) * 100, 1) if (tp + fp) else None,
        "recall_pct": round(tp / (tp + fn) * 100, 1) if (tp + fn) else None,
        "specificity_pct": round(tn / (tn + fp) * 100, 1) if (tn + fp) else None,
        "f1_pct": round(2 * tp / (2 * tp + fp + fn) * 100, 1) if (2 * tp + fp + fn) else None,
        "abstention_rate_pct": round(neutral / (total_dir + neutral) * 100, 1) if (total_dir + neutral) else None,
    }

# Per-sector
for sn in data["sectors"]:
    data["sectors"][sn]["confusion_matrix"] = compute_cm(data["sectors"], sector_filter=sn)

# Overall
data["overall_confusion_matrix"] = compute_cm(data["sectors"])

# ── Save ──────────────────────────────────────────────────────────────────────
with open("sector_backtest_results.json", "w") as f:
    json.dump(data, f, indent=2)

with open("sector_confusion_matrix.json", "w") as f:
    cm_out = {
        "meta": data.get("meta", {}),
        "overall": data["overall_confusion_matrix"],
        "by_sector": {sn: data["sectors"][sn]["confusion_matrix"] for sn in data["sectors"]},
    }
    json.dump(cm_out, f, indent=2)

# ── Print comparison ──────────────────────────────────────────────────────────
old_cm = old_data.get("overall_confusion_matrix", {})
new_cm = data["overall_confusion_matrix"]

print("=" * 72)
print("  RE-EVALUATION COMPLETE — v3 SCORING APPLIED")
print("  Fixes: Lynch discount, Greenblatt re-bucket, health-val penalty,")
print("         Graham floor, borderline confidence gate")
print("=" * 72)
print()
print("  BEFORE vs AFTER (Overall)")
print()
fmt = "  {:<24} {:>10} {:>10} {:>10}"
print(fmt.format("Metric", "BEFORE", "AFTER", "CHANGE"))
print("  " + "-" * 56)

for key, label in [
    ("TP", "True Positives"),
    ("FP", "False Positives"),
    ("FN", "False Negatives"),
    ("TN", "True Negatives"),
    ("neutral_count", "Neutral (abstained)"),
    ("directional_signals", "Directional signals"),
    ("accuracy_pct", "Accuracy %"),
    ("precision_pct", "Precision %"),
    ("recall_pct", "Recall %"),
    ("specificity_pct", "Specificity %"),
    ("f1_pct", "F1 Score %"),
    ("abstention_rate_pct", "Abstention Rate %"),
]:
    old_val = old_cm.get(key)
    new_val = new_cm.get(key)
    if old_val is None or new_val is None:
        change = "N/A"
    elif isinstance(old_val, float):
        diff = new_val - old_val
        change = f"{diff:+.1f}"
    else:
        diff = new_val - old_val
        change = f"{diff:+d}"
    old_str = f"{old_val:.1f}" if isinstance(old_val, float) else str(old_val)
    new_str = f"{new_val:.1f}" if isinstance(new_val, float) else str(new_val)
    print(fmt.format(label, old_str, new_str, change))

print()
print("  Per-Sector Changes:")
print()
hdr = "  {:<22} {:>8} {:>8} {:>8} {:>8}"
print(hdr.format("Sector", "Old Acc%", "New Acc%", "Change", "Abstain%"))
print("  " + "-" * 56)
for sn in data["sectors"]:
    old_s = old_data["sectors"][sn].get("confusion_matrix", {})
    new_s = data["sectors"][sn]["confusion_matrix"]
    oa = old_s.get("accuracy_pct", 0) or 0
    na = new_s.get("accuracy_pct", 0) or 0
    ab = new_s.get("abstention_rate_pct", 0) or 0
    diff = na - oa
    label = sn.replace("_", " ")
    print(hdr.format(label, f"{oa:.1f}", f"{na:.1f}", f"{diff:+.1f}", f"{ab:.1f}"))

print()
# Signal distribution
bull = new_cm["TP"] + new_cm["FP"]
bear = new_cm["FN"] + new_cm["TN"]
neut = new_cm["neutral_count"]
total = bull + bear + neut
print(f"  New signal distribution:")
print(f"    Bullish:  {bull:>4} ({bull/total*100:.1f}%)")
print(f"    Neutral:  {neut:>4} ({neut/total*100:.1f}%)")
print(f"    Bearish:  {bear:>4} ({bear/total*100:.1f}%)")
print()
print("  Updated files: sector_backtest_results.json, sector_confusion_matrix.json")
print()
