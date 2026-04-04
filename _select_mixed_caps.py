#!/usr/bin/env python3
"""
_select_mixed_caps.py
=====================
Read halal_by_sector.json (ONLY source of truth),
fetch market-cap from yfinance, classify L/M/S,
pick 5 mixed-cap per sector (2L + 2M + 1S).

Uses existing Polygon cache for known tickers, falls back to yfinance.
Output -> data/input/master_data/halal_top5_per_sector.json
"""
import json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).parent
INPUT_PATH  = ROOT / "data" / "input" / "master_data" / "halal_by_sector.json"
OUTPUT_PATH = ROOT / "data" / "input" / "master_data" / "halal_top5_per_sector.json"
CACHE_PATH  = ROOT / "data" / "input" / "master_data" / "_market_cap_cache.json"

LARGE_MIN = 10_000_000_000   # >= $10B
MID_MIN   =  2_000_000_000   # >= $2B

def classify(mc):
    if mc >= LARGE_MIN: return "large"
    if mc >= MID_MIN:   return "mid"
    return "small"

def fetch_mc_yf(ticker):
    """Fetch market cap using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.fast_info
        mc = getattr(info, 'market_cap', None)
        if mc and mc > 0:
            return float(mc)
        # Fallback to info dict
        info_dict = t.info
        mc = info_dict.get('marketCap', 0)
        return float(mc) if mc and mc > 0 else 0
    except Exception:
        return 0

# Load input
with open(INPUT_PATH) as f:
    by_sector = json.load(f)

all_tickers = sorted(set(t for tl in by_sector.values() for t in tl))
print("Total tickers: {}".format(len(all_tickers)), flush=True)

# Load existing cache (from Polygon partial run)
cache = {}
if CACHE_PATH.exists():
    with open(CACHE_PATH) as f:
        cache = json.load(f)
    # Only keep non-zero entries
    cache = {k: v for k, v in cache.items() if v > 0}
    print("Cache: {} valid entries".format(len(cache)), flush=True)

# Fetch missing with yfinance (parallel, 10 threads)
to_fetch = [t for t in all_tickers if t not in cache]
print("To fetch via yfinance: {}".format(len(to_fetch)), flush=True)

if to_fetch:
    done = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_mc_yf, t): t for t in to_fetch}
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                mc = fut.result()
            except Exception:
                mc = 0
            cache[ticker] = mc
            if mc > 0:
                done += 1
            else:
                failed += 1
            total_done = done + failed
            if total_done % 50 == 0:
                print("  {}/{} fetched ({} unknown)".format(total_done, len(to_fetch), failed), flush=True)

    print("Fetched: {} OK, {} unknown".format(done, failed), flush=True)

# Save cache
with open(CACHE_PATH, "w") as f:
    json.dump(cache, f, indent=2)
print("Cache saved ({} entries)".format(len(cache)), flush=True)

# Build selection
result = {}
for sec in sorted(by_sector):
    tickers = by_sector[sec]
    items = []
    for t in tickers:
        mc = cache.get(t, 0)
        items.append({"ticker": t, "mc": mc, "cap": classify(mc) if mc > 0 else "unknown"})

    large = sorted([x for x in items if x["cap"] == "large"], key=lambda x: -x["mc"])
    mid   = sorted([x for x in items if x["cap"] == "mid"],   key=lambda x: -x["mc"])
    small = sorted([x for x in items if x["cap"] == "small"], key=lambda x: -x["mc"])
    unk   = [x for x in items if x["cap"] == "unknown"]

    # 2 large + 2 mid + 1 small
    picks = large[:2] + mid[:2] + small[:1]
    picked = set(p["ticker"] for p in picks)
    for pool in [large, mid, small, unk]:
        for x in pool:
            if len(picks) >= 5: break
            if x["ticker"] not in picked:
                picks.append(x)
                picked.add(x["ticker"])

    result[sec] = [{"ticker": p["ticker"], "cap_tier": p["cap"], "market_cap": p["mc"]} for p in picks]

with open(OUTPUT_PATH, "w") as f:
    json.dump(result, f, indent=2)

# Summary
print("\n--- SELECTION ---", flush=True)
total = 0
for sec in sorted(result):
    ts = result[sec]
    total += len(ts)
    disp = ", ".join("{} ({})".format(t["ticker"], t["cap_tier"][0].upper()) for t in ts)
    print("  {:<28} {}: {}".format(sec, len(ts), disp), flush=True)
print("\nTOTAL: {} tickers, {} sectors".format(total, len(result)), flush=True)
print("Saved -> {}".format(OUTPUT_PATH), flush=True)
