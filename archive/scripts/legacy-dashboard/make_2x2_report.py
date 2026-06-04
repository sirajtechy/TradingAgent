import json

with open("sector_backtest_results.json") as f:
    data = json.load(f)

# 2x2 Confusion Matrix: Bullish vs Bearish ONLY (Neutral set aside)
overall = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
sector_cm = {}
neutral_total = 0

for sn in data["sectors"]:
    sector_cm[sn] = {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "neutral": 0}

for sector_name, sector in data["sectors"].items():
    for ticker, tdata in sector["tickers"].items():
        if not isinstance(tdata, dict):
            continue
        for p in tdata.get("periods", []):
            if not isinstance(p, dict):
                continue
            sig = (p.get("signal") or "").lower()
            act = (p.get("actual_direction") or "").lower()

            if "bullish" not in sig and "bearish" not in sig:
                neutral_total += 1
                sector_cm[sector_name]["neutral"] += 1
                continue

            if "bullish" in sig and act == "up":
                cell = "TP"
            elif "bullish" in sig and act == "down":
                cell = "FP"
            elif "bearish" in sig and act == "up":
                cell = "FN"
            elif "bearish" in sig and act == "down":
                cell = "TN"
            else:
                continue

            overall[cell] += 1
            sector_cm[sector_name][cell] += 1

DIV = "=" * 72
DIV2 = "-" * 72


def metrics(cm):
    tp, fp, fn, tn = cm["TP"], cm["FP"], cm["FN"], cm["TN"]
    total = tp + fp + fn + tn
    acc = (tp + tn) / total * 100 if total else 0
    prec = tp / (tp + fp) * 100 if (tp + fp) else 0
    rec = tp / (tp + fn) * 100 if (tp + fn) else 0
    spec = tn / (tn + fp) * 100 if (tn + fp) else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    npv = tn / (tn + fn) * 100 if (tn + fn) else 0
    return {"total": total, "acc": acc, "prec": prec, "rec": rec,
            "spec": spec, "f1": f1, "npv": npv}


def print_2x2(cm, label):
    tp, fp, fn, tn = cm["TP"], cm["FP"], cm["FN"], cm["TN"]
    m = metrics(cm)
    print(f"\n  [ {label} ]")
    hdr = f"  {'':>18} | {'Actual: UP':>12} | {'Actual: DOWN':>12} | {'ROW TOTAL':>10}"
    print(hdr)
    print("  " + DIV2)
    print(f"  {'Pred: BULLISH':>18} | {tp:>12} | {fp:>12} | {tp+fp:>10}")
    print(f"  {'Pred: BEARISH':>18} | {fn:>12} | {tn:>12} | {fn+tn:>10}")
    print("  " + DIV2)
    print(f"  {'COL TOTAL':>18} | {tp+fn:>12} | {fp+tn:>12} | {m['total']:>10}")
    print()
    print(f"    Accuracy    = {m['acc']:>6.1f}%    Precision   = {m['prec']:>6.1f}%")
    print(f"    Recall      = {m['rec']:>6.1f}%    Specificity = {m['spec']:>6.1f}%")
    print(f"    F1-Score    = {m['f1']:>6.1f}%    NPV         = {m['npv']:>6.1f}%")


# ── REPORT ───────────────────────────────────────────────────────────────────

tp, fp, fn, tn = overall["TP"], overall["FP"], overall["FN"], overall["TN"]
total_dir = tp + fp + fn + tn

print()
print(DIV)
print("  FUNDAMENTAL ANALYSIS AGENT - 2x2 CONFUSION MATRIX REPORT")
print("  (Bullish vs Bearish only - Neutral signals EXCLUDED)")
print(f"  Window: Mar 2025 - Feb 2026  |  5 sectors  |  59 tickers  |  12 months")
print(DIV)

print(f"\n  Directional signals: {total_dir}   |   Neutral (set aside): {neutral_total}   |   Grand total: {total_dir + neutral_total}")

# ── SECTION 1 ────────────────────────────────────────────────────────────────
print()
print("--- SECTION 1: OVERALL 2x2 CONFUSION MATRIX ---")
print()
print("  Rows = What the agent PREDICTED  (Bullish / Bearish)")
print("  Cols = What price actually DID    (Went Up / Went Down)")
print()
print("  TP = Bullish + Price Up    = correct buy signal")
print("  FP = Bullish + Price Down  = wrong buy signal")
print("  FN = Bearish + Price Up    = missed opportunity")
print("  TN = Bearish + Price Down  = correct avoid signal")
print_2x2(overall, "ALL SECTORS - DIRECTIONAL ONLY")

# ── RECONCILIATION ───────────────────────────────────────────────────────────
print()
print("--- RECONCILIATION CHECK ---")
print()
print(f"  TP + FP + FN + TN = {tp} + {fp} + {fn} + {tn} = {total_dir}")
print(f"  Neutral excluded  = {neutral_total}")
print(f"  Total periods     = {total_dir} + {neutral_total} = {total_dir + neutral_total}")
orig = data.get("overall_confusion_matrix", {})
orig_tp = orig.get("TP", 0)
orig_fp = orig.get("FP", 0)
orig_tn = orig.get("TN", 0)
orig_fn = orig.get("FN", 0)
orig_neut = orig.get("neutral_count", 0)
print(f"\n  Cross-check with stored confusion matrix:")
print(f"    Stored: TP={orig_tp}  FP={orig_fp}  FN={orig_fn}  TN={orig_tn}  Neutral={orig_neut}")
print(f"    Ours:   TP={tp}  FP={fp}  FN={fn}  TN={tn}  Neutral={neutral_total}")
match_ok = (tp == orig_tp and fp == orig_fp and fn == orig_fn and tn == orig_tn and neutral_total == orig_neut)
print(f"    Match: {'YES - all values reconcile' if match_ok else 'MISMATCH - investigate'}")

# ── SECTION 2 ────────────────────────────────────────────────────────────────
print()
print("--- SECTION 2: PER-SECTOR 2x2 BREAKDOWN ---")

sector_rows = []
for sn, cm in sector_cm.items():
    label = sn.replace("_", " ")
    neut = cm.pop("neutral", 0)
    print_2x2(cm, label.upper())
    m = metrics(cm)
    sector_rows.append((label, m["total"], neut, m["acc"], m["prec"],
                         m["rec"], m["spec"], m["f1"]))
    cm["neutral"] = neut

# ── SECTION 3 ────────────────────────────────────────────────────────────────
print()
print("--- SECTION 3: SECTOR LEADERBOARD ---")
print()
hdr = f"  {'Sector':<22} {'Calls':>6} {'Neut':>6} {'Acc%':>7} {'Prec%':>7} {'Rec%':>7} {'Spec%':>7} {'F1%':>7}"
print(hdr)
print("  " + DIV2)
ranked = sorted(sector_rows, key=lambda x: x[3], reverse=True)
for i, (sl, tot, neut, acc, prec, rec, spec, f1) in enumerate(ranked, 1):
    bar = "#" * int(acc / 5)
    print(f"  {i}. {sl:<20} {tot:>6} {neut:>6} {acc:>7.1f} {prec:>7.1f} {rec:>7.1f} {spec:>7.1f} {f1:>7.1f}  {bar}")

# ── SECTION 4 ────────────────────────────────────────────────────────────────
print()
print("--- SECTION 4: SIGNAL BIAS & INTERPRETATION ---")
print()
bull = tp + fp
bear = fn + tn
print(f"  Bullish calls: {bull} ({bull/total_dir*100:.1f}%)   Bearish calls: {bear} ({bear/total_dir*100:.1f}%)")
if bear:
    print(f"  Ratio: {bull/bear:.1f}:1 bullish-to-bearish")
print()
print(f"  When the agent said BULLISH ({bull} times):")
print(f"    Price went UP:   {tp} times ({tp/bull*100:.1f}%)  CORRECT")
print(f"    Price went DOWN: {fp} times ({fp/bull*100:.1f}%)  WRONG")
print()
if bear:
    print(f"  When the agent said BEARISH ({bear} times):")
    print(f"    Price went DOWN: {tn} times ({tn/bear*100:.1f}%)  CORRECT")
    print(f"    Price went UP:   {fn} times ({fn/bear*100:.1f}%)  WRONG")
    print()
actual_up = tp + fn
actual_down = fp + tn
print(f"  When price actually went UP ({actual_up} times):")
print(f"    Agent said Bullish: {tp} ({tp/actual_up*100:.1f}%)   Bearish: {fn} ({fn/actual_up*100:.1f}%)")
print()
print(f"  When price actually went DOWN ({actual_down} times):")
print(f"    Agent said Bullish: {fp} ({fp/actual_down*100:.1f}%)   Bearish: {tn} ({tn/actual_down*100:.1f}%)")

print()
print(DIV)
print("  END OF 2x2 REPORT")
print(DIV)
print()
