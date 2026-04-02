#!/usr/bin/env python3
"""Regression test: compare v3 predictions against baseline."""
import json

with open("baseline_predictions.json") as f:
    baseline = {b["key"]: b for b in json.load(f)}

with open("sector_backtest_results.json") as f:
    data = json.load(f)

new_preds = {}
for sn, sector in data["sectors"].items():
    for ticker, tdata in sector["tickers"].items():
        if not tdata or not tdata.get("periods"):
            continue
        for p in tdata["periods"]:
            key = f"{ticker}_{p['signal_date']}"
            new_preds[key] = {
                "signal": p["signal"],
                "signal_correct": p["signal_correct"],
                "score": p["experimental_score"],
                "band": p["score_band"],
                "actual": p["actual_direction"],
            }

regressions = []
correct_to_neutral = []
fixed_to_correct = []
fixed_to_neutral = []
neutral_to_correct = []
neutral_to_wrong = []

for key, old in baseline.items():
    new = new_preds.get(key)
    if not new:
        continue
    old_c = old["signal_correct"]
    new_c = new["signal_correct"]

    if old_c is True and new_c is False:
        regressions.append((key, old, new))
    elif old_c is True and new_c is None:
        correct_to_neutral.append((key, old, new))
    elif old_c is False and new_c is True:
        fixed_to_correct.append((key, old, new))
    elif old_c is False and new_c is None:
        fixed_to_neutral.append((key, old, new))
    elif old_c is None and new_c is True:
        neutral_to_correct.append((key, old, new))
    elif old_c is None and new_c is False:
        neutral_to_wrong.append((key, old, new))

print("=" * 72)
print("  REGRESSION TEST — v2 Baseline vs v3 Scoring")
print("=" * 72)
print()
print(f"  Previously CORRECT -> now WRONG:       {len(regressions)}")
print(f"  Previously CORRECT -> now neutral:     {len(correct_to_neutral)}")
print(f"  Previously WRONG   -> now CORRECT:     {len(fixed_to_correct)}")
print(f"  Previously WRONG   -> now neutral:     {len(fixed_to_neutral)}")
print(f"  Previously neutral -> now CORRECT:     {len(neutral_to_correct)}")
print(f"  Previously neutral -> now WRONG:       {len(neutral_to_wrong)}")
print()

net_correct = len(fixed_to_correct) + len(neutral_to_correct) - len(regressions) - len(correct_to_neutral)
net_wrong = len(neutral_to_wrong) - len(fixed_to_correct) - len(fixed_to_neutral)
print(f"  Net change in correct predictions:     {net_correct:+d}")
print(f"  Net change in wrong predictions:       {net_wrong:+d}")
print()

if regressions:
    print("-" * 72)
    print("  REGRESSIONS (was correct, now wrong):")
    print("-" * 72)
    for key, old, new in sorted(regressions):
        print(f"  {key}: {old['signal']}->{new['signal']}  "
              f"actual={old['actual']}  score={old['score']}->{new['score']}")
    print()

if neutral_to_wrong:
    print("-" * 72)
    print("  NEW ERRORS (was neutral, now wrong):")
    print("-" * 72)
    for key, old, new in sorted(neutral_to_wrong):
        print(f"  {key}: neutral->{new['signal']}  "
              f"actual={old['actual']}  score={old['score']}->{new['score']}")
    print()

if fixed_to_correct:
    print("-" * 72)
    print(f"  FIXED (was wrong, now correct): {len(fixed_to_correct)}")
    print("-" * 72)
    for key, old, new in sorted(fixed_to_correct):
        print(f"  {key}: {old['signal']}->{new['signal']}  "
              f"actual={old['actual']}  score={old['score']}->{new['score']}")
    print()

if fixed_to_neutral:
    print("-" * 72)
    print(f"  IMPROVED (was wrong, now neutral/abstained): {len(fixed_to_neutral)}")
    print("-" * 72)
    for key, old, new in sorted(fixed_to_neutral):
        print(f"  {key}: {old['signal']}->neutral  "
              f"actual={old['actual']}  score={old['score']}->{new['score']}")
