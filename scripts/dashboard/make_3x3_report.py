import json
from collections import defaultdict

with open("sector_backtest_results.json") as f:
    data = json.load(f)

# 3x3 Confusion Matrix
# Rows = Predicted Signal: Bullish | Neutral | Bearish
# Cols = Actual Outcome:   Up      | Flat    | Down

matrix = {
    'Bullish': {'Up': 0, 'Flat': 0, 'Down': 0},
    'Neutral':  {'Up': 0, 'Flat': 0, 'Down': 0},
    'Bearish':  {'Up': 0, 'Flat': 0, 'Down': 0},
}

# Per-sector 3x3
sector_matrix = {}
for sn in data['sectors']:
    sector_matrix[sn] = {
        'Bullish': {'Up': 0, 'Flat': 0, 'Down': 0},
        'Neutral':  {'Up': 0, 'Flat': 0, 'Down': 0},
        'Bearish':  {'Up': 0, 'Flat': 0, 'Down': 0},
    }

total_periods = 0
skipped = 0

for sector_name, sector in data['sectors'].items():
    for ticker, tdata in sector['tickers'].items():
        if not isinstance(tdata, dict):
            continue
        for p in tdata.get('periods', []):
            if not isinstance(p, dict):
                skipped += 1
                continue
            total_periods += 1
            sig = (p.get('signal') or '').lower()
            act = (p.get('actual_direction') or '').lower()

            if 'bullish' in sig:
                row = 'Bullish'
            elif 'bearish' in sig:
                row = 'Bearish'
            else:
                row = 'Neutral'

            if act == 'up':
                col = 'Up'
            elif act == 'down':
                col = 'Down'
            else:
                col = 'Flat'

            matrix[row][col] += 1
            sector_matrix[sector_name][row][col] += 1

grand_total = sum(matrix[r][c] for r in matrix for c in ['Up','Flat','Down'])

# ─── PRINT REPORT ───────────────────────────────────────────────────────────

DIVIDER = "=" * 72
DIV2    = "-" * 72

def print_3x3(m, label=""):
    if label:
        print(f"\n  [ {label} ]")
    rows = ['Bullish', 'Neutral', 'Bearish']
    cols = ['Up', 'Flat', 'Down']
    head = f"  {'Predicted':>14} | {'Actual: UP':>10} | {'Actual: FLAT':>12} | {'Actual: DOWN':>12} | {'TOTAL':>7}"
    print(head)
    print("  " + DIV2)
    for row in rows:
        r  = m[row]
        t  = r['Up'] + r['Flat'] + r['Down']
        print(f"  {'Pred: ' + row:>14} | {r['Up']:>10} | {r['Flat']:>12} | {r['Down']:>12} | {t:>7}")
    print("  " + DIV2)
    cu = sum(m[r]['Up']   for r in rows)
    cf = sum(m[r]['Flat'] for r in rows)
    cd = sum(m[r]['Down'] for r in rows)
    gt = cu + cf + cd
    print(f"  {'COL TOTAL':>14} | {cu:>10} | {cf:>12} | {cd:>12} | {gt:>7}")


def per_class_metrics(m):
    rows  = ['Bullish', 'Neutral', 'Bearish']
    total = sum(m[r][c] for r in rows for c in ['Up','Flat','Down'])
    lines = []
    for pred_class, act_class in [('Bullish','Up'), ('Bearish','Down'), ('Neutral','Flat')]:
        TP = m[pred_class][act_class]
        FP = sum(m[pred_class][c] for c in ['Up','Flat','Down'] if c != act_class)
        FN = sum(m[r][act_class]  for r in rows if r != pred_class)
        TN = total - TP - FP - FN
        prec = TP / (TP + FP) * 100 if (TP + FP) > 0 else 0
        rec  = TP / (TP + FN) * 100 if (TP + FN) > 0 else 0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        lines.append((pred_class, act_class, TP, FP, FN, TN, prec, rec, f1))
    return lines


def macro_avg(lines):
    p = sum(l[6] for l in lines) / len(lines)
    r = sum(l[7] for l in lines) / len(lines)
    f = sum(l[8] for l in lines) / len(lines)
    return p, r, f


print()
print(DIVIDER)
print("  FUNDAMENTAL ANALYSIS AGENT — BACKTEST CONFUSION MATRIX REPORT")
print(f"  Window : Mar 2025 – Feb 2026  (12 months)")
print(f"  Sectors: 5  |  Tickers: 59 active (1 error)  |  Total periods: {total_periods}")
print(DIVIDER)

print()
print("─── SECTION 1: OVERALL 3×3 CONFUSION MATRIX ───────────────────────────")
print()
print("  Rows   = What the agent PREDICTED  (Bullish / Neutral / Bearish)")
print("  Cols   = What the market DID       (Price Up / Flat / Price Down)")
print()
print_3x3(matrix, "ALL SECTORS COMBINED")

print()
print("  Interpretation key:")
print("  • Bullish + Up     = TP (True Positive)  — correct bullish call")
print("  • Bearish + Down   = TN (True Negative)  — correct bearish call")
print("  • Bullish + Down   = FP (False Positive) — bullish but price fell")
print("  • Bearish + Up     = FN (False Negative) — bearish but price rose")
print("  • Neutral + Up/Down= Abstention          — agent withheld a call")

print()
print("─── SECTION 2: PER-CLASS METRICS (OvR decomposition) ──────────────────")
print()
lines = per_class_metrics(matrix)
print(f"  {'Class':<12} {'Actual':<10} {'TP':>5} {'FP':>5} {'FN':>5} {'TN':>5}  {'Prec%':>7} {'Rec%':>7} {'F1%':>7}")
print("  " + DIV2)
for (pred_class, act_class, TP, FP, FN, TN, prec, rec, f1) in lines:
    print(f"  {pred_class:<12} {act_class:<10} {TP:>5} {FP:>5} {FN:>5} {TN:>5}  {prec:>7.1f} {rec:>7.1f} {f1:>7.1f}")
print("  " + DIV2)
mp, mr, mf = macro_avg(lines)
print(f"  {'Macro Avg':<12} {'':10} {'':>5} {'':>5} {'':>5} {'':>5}  {mp:>7.1f} {mr:>7.1f} {mf:>7.1f}")

print()
overall = data['overall_confusion_matrix'] if 'overall_confusion_matrix' in data else data.get('meta',{})
cm = data.get('overall_confusion_matrix', {}).get('overall', {})
# Recompute from matrix directly
total_dir   = sum(matrix[r][c] for r in ['Bullish','Bearish'] for c in ['Up','Flat','Down'])
total_neut  = sum(matrix['Neutral'][c] for c in ['Up','Flat','Down'])
correct_dir = matrix['Bullish']['Up'] + matrix['Bearish']['Down']
accuracy    = correct_dir / total_dir * 100 if total_dir else 0
abstent     = total_neut / (total_periods) * 100 if total_periods else 0

print("─── SECTION 3: SUMMARY STATISTICS ─────────────────────────────────────")
print()
print(f"  Total observations     : {total_periods:>6}")
print(f"  Directional calls      : {total_dir:>6}  ({total_dir/total_periods*100:.1f}% of all periods)")
print(f"  Neutral / Abstentions  : {total_neut:>6}  ({abstent:.1f}% of all periods)")
print()
print(f"  Correct directional    : {correct_dir:>6}")
print(f"  Directional accuracy   : {accuracy:>6.1f}%")
print()
print(f"  Price went Up   (total): {sum(matrix[r]['Up']   for r in matrix):>6}")
print(f"  Price was Flat  (total): {sum(matrix[r]['Flat'] for r in matrix):>6}")
print(f"  Price went Down (total): {sum(matrix[r]['Down'] for r in matrix):>6}")
print()
# Macro / Weighted
macro_p, macro_r, macro_f = macro_avg(lines)
print(f"  Macro-avg Precision    : {macro_p:>6.1f}%")
print(f"  Macro-avg Recall       : {macro_r:>6.1f}%")
print(f"  Macro-avg F1-Score     : {macro_f:>6.1f}%")

print()
print("─── SECTION 4: PER-SECTOR 3×3 BREAKDOWN ───────────────────────────────")

sector_summary = []
for sn, sm in sector_matrix.items():
    print()
    sector_label = sn.replace("_", " ")
    print(f"  ┌─ {sector_label.upper()} ─────────────────────────────────────────────────────")
    print_3x3(sm, sector_label)
    slines = per_class_metrics(sm)
    sp, sr, sf = macro_avg(slines)
    sd   = sum(sm[r][c] for r in ['Bullish','Bearish'] for c in ['Up','Flat','Down'])
    sn2  = sum(sm['Neutral'][c] for c in ['Up','Flat','Down'])
    sc   = sm['Bullish']['Up'] + sm['Bearish']['Down']
    sacc = sc / sd * 100 if sd else 0
    sector_summary.append((sector_label, sd, sn2, sc, sacc, sp, sr, sf))
    print()
    print(f"    Directional calls: {sd}   Abstentions: {sn2}   Correct: {sc}   Accuracy: {sacc:.1f}%")
    print(f"    Macro Prec: {sp:.1f}%   Macro Rec: {sr:.1f}%   Macro F1: {sf:.1f}%")

print()
print("─── SECTION 5: SECTOR COMPARISON LEADERBOARD ──────────────────────────")
print()
print(f"  {'Sector':<22} {'Dir.Calls':>10} {'Abstain':>8} {'Correct':>8} {'Acc%':>7} {'MacroF1%':>10}")
print("  " + DIV2)
ranked = sorted(sector_summary, key=lambda x: x[4], reverse=True)
for rank, (sl, sd, sn2, sc, sacc, sp, sr, sf) in enumerate(ranked, 1):
    bar = '█' * int(sacc / 5)
    print(f"  {rank}. {sl:<20} {sd:>10} {sn2:>8} {sc:>8} {sacc:>7.1f}% {sf:>9.1f}%  {bar}")

print()
print("─── SECTION 6: SIGNAL BIAS ANALYSIS ───────────────────────────────────")
print()
total_bull = sum(matrix['Bullish'][c] for c in ['Up','Flat','Down'])
total_bear = sum(matrix['Bearish'][c] for c in ['Up','Flat','Down'])
total_neut2 = sum(matrix['Neutral'][c] for c in ['Up','Flat','Down'])
print(f"  The agent issued {total_bull} Bullish calls ({total_bull/total_periods*100:.1f}%),")
print(f"  {total_bear} Bearish calls ({total_bear/total_periods*100:.1f}%),")
print(f"  and {total_neut2} Neutral/abstain signals ({total_neut2/total_periods*100:.1f}%).")
print()
print(f"  Bullish hit rate (TP / all Bullish):  {matrix['Bullish']['Up']}/{total_bull} = {matrix['Bullish']['Up']/total_bull*100:.1f}%")
print(f"  Bearish hit rate (TN / all Bearish):  {matrix['Bearish']['Down']}/{total_bear} = {matrix['Bearish']['Down']/total_bear*100:.1f}%" if total_bear else "  Bearish hit rate: N/A (no bearish calls)")
print()
print(f"  When price went UP:   {matrix['Bullish']['Up']} Bullish ✓, {matrix['Neutral']['Up']} Neutral (missed), {matrix['Bearish']['Up']} Bearish ✗")
print(f"  When price went DOWN: {matrix['Bearish']['Down']} Bearish ✓, {matrix['Neutral']['Down']} Neutral (missed), {matrix['Bullish']['Down']} Bullish ✗")
print(f"  When price was FLAT:  {matrix['Neutral']['Flat']} Neutral ✓, {matrix['Bullish']['Flat']} Bullish (over-call), {matrix['Bearish']['Flat']} Bearish (over-call)")

print()
print(DIVIDER)
print("  END OF REPORT")
print(DIVIDER)
print()
