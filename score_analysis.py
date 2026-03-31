"""Analyze the score distribution to find optimal thresholds."""
import json

with open("sector_backtest_results.json") as f:
    data = json.load(f)

scores_up = []
scores_down = []

for sector in data["sectors"].values():
    for tdata in sector["tickers"].values():
        if not isinstance(tdata, dict):
            continue
        for p in tdata.get("periods", []):
            if not isinstance(p, dict):
                continue
            score = p.get("experimental_score")
            act = (p.get("actual_direction") or "").lower()
            if score is None:
                continue
            if act == "up":
                scores_up.append(score)
            elif act == "down":
                scores_down.append(score)

all_scores = scores_up + scores_down
all_scores.sort()

print(f"Total scored periods: {len(all_scores)}")
print(f"  Price went UP: {len(scores_up)}   Price went DOWN: {len(scores_down)}")
print()

# Distribution
print("Score distribution (all):")
buckets = [(0,35),(35,40),(40,45),(45,50),(50,55),(55,60),(60,65),(65,70),(70,75),(75,80),(80,85),(85,100)]
print(f"  {'Range':>10}  {'Count':>6}  {'Up':>5}  {'Down':>5}  {'Up%':>6}  Bar")
print("  " + "-" * 60)
for lo, hi in buckets:
    n_up = sum(1 for s in scores_up if lo <= s < hi)
    n_dn = sum(1 for s in scores_down if lo <= s < hi)
    total = n_up + n_dn
    pct = n_up / total * 100 if total else 0
    bar_up = "#" * int(n_up / 3)
    bar_dn = "." * int(n_dn / 3)
    print(f"  {lo:>3}-{hi:<3}     {total:>6}  {n_up:>5}  {n_dn:>5}  {pct:>5.1f}%  {bar_up}{bar_dn}")

print()
print("Percentiles:")
for pctl in [10, 25, 50, 75, 90]:
    idx = int(len(all_scores) * pctl / 100)
    print(f"  P{pctl}: {all_scores[idx]:.1f}")

print()
print("Accuracy at each threshold (if bullish >= X, neutral otherwise):")
print(f"  {'Threshold':>10}  {'Bullish':>8}  {'TP':>5}  {'FP':>5}  {'Acc%':>7}  {'Prec%':>7}  {'Coverage%':>10}")
print("  " + "-" * 65)
for thresh in [50, 52, 54, 55, 56, 57, 58, 59, 60, 62, 64, 65, 70]:
    bull_up = sum(1 for s in scores_up if s >= thresh)
    bull_dn = sum(1 for s in scores_down if s >= thresh)
    total_bull = bull_up + bull_dn
    if total_bull == 0:
        continue
    acc = bull_up / total_bull * 100
    coverage = total_bull / len(all_scores) * 100
    print(f"  {thresh:>10}  {total_bull:>8}  {bull_up:>5}  {bull_dn:>5}  {acc:>7.1f}  {acc:>7.1f}  {coverage:>9.1f}%")

print()
print("Accuracy at bearish threshold (if score < X, and price went down):")
print(f"  {'Threshold':>10}  {'Bearish':>8}  {'TN':>5}  {'FN':>5}  {'Acc%':>7}  {'Coverage%':>10}")
print("  " + "-" * 55)
for thresh in [35, 40, 42, 44, 45, 46, 48, 50, 52, 55]:
    bear_dn = sum(1 for s in scores_down if s < thresh)
    bear_up = sum(1 for s in scores_up if s < thresh)
    total_bear = bear_up + bear_dn
    if total_bear == 0:
        continue
    acc = bear_dn / total_bear * 100
    coverage = total_bear / len(all_scores) * 100
    print(f"  {thresh:>10}  {total_bear:>8}  {bear_dn:>5}  {bear_up:>5}  {acc:>7.1f}  {coverage:>9.1f}%")

print()
print("Combined threshold sweep (bullish >= X, bearish < Y):")
print(f"  {'Bull>=':>7} {'Bear<':>6} {'Calls':>6} {'Corr':>5} {'Acc%':>7} {'Neut%':>7} {'Prec%':>7} {'Spec%':>7}")
print("  " + "-" * 65)
best_acc = 0
best_combo = None
for bt in [55, 56, 57, 58, 59, 60, 62]:
    for brt in [45, 48, 50, 52, 55]:
        tp = sum(1 for s in scores_up if s >= bt)
        fp = sum(1 for s in scores_down if s >= bt)
        tn = sum(1 for s in scores_down if s < brt)
        fn = sum(1 for s in scores_up if s < brt)
        dir_total = tp + fp + fn + tn
        neut = len(all_scores) - dir_total
        correct = tp + tn
        if dir_total == 0:
            continue
        acc = correct / dir_total * 100
        neut_pct = neut / len(all_scores) * 100
        prec = tp / (tp + fp) * 100 if (tp + fp) else 0
        spec = tn / (tn + fp) * 100 if (tn + fp) else 0
        if acc > best_acc and neut_pct < 70:
            best_acc = acc
            best_combo = (bt, brt, dir_total, correct, acc, neut_pct, prec, spec)
        print(f"  {bt:>7} {brt:>6} {dir_total:>6} {correct:>5} {acc:>7.1f} {neut_pct:>7.1f} {prec:>7.1f} {spec:>7.1f}")

if best_combo:
    print()
    bt, brt, d, c, a, n, p, s = best_combo
    print(f"  BEST combo (acc, abstention < 70%): Bull >= {bt}, Bear < {brt}")
    print(f"  Accuracy: {a:.1f}%  Calls: {d}  Neutral: {n:.1f}%  Precision: {p:.1f}%  Specificity: {s:.1f}%")
