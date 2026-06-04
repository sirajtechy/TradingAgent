#!/usr/bin/env python3
"""Clean and categorize the master halal tickers JSON, then pick 5 per sector for testing."""
import json
from pathlib import Path
from collections import defaultdict

RAW = Path("data/input/master_data/halal_tickers_sector.json")
OUT_CLEAN = Path("data/input/master_data/halal_tickers_clean.json")
OUT_BY_SECTOR = Path("data/input/master_data/halal_by_sector.json")
OUT_TOP5 = Path("data/input/master_data/halal_top5_per_sector.json")

raw = json.loads(RAW.read_text())

# 1. Clean trailing commas from tickers
cleaned = []
for r in raw:
    t = r["ticker"].rstrip(",").strip()
    if t:
        cleaned.append({"ticker": t, "sector": r["sector"]})
OUT_CLEAN.write_text(json.dumps(cleaned, indent=2))
print(f"Cleaned: {len(cleaned)} tickers → {OUT_CLEAN}")

# 2. Group by sector
by_sector = defaultdict(list)
for r in cleaned:
    by_sector[r["sector"]].append(r["ticker"])
by_sector = dict(sorted(by_sector.items()))
OUT_BY_SECTOR.write_text(json.dumps(by_sector, indent=2))
print(f"By sector: {len(by_sector)} sectors → {OUT_BY_SECTOR}")
for s, tickers in by_sector.items():
    print(f"  {s}: {len(tickers)} tickers")

# 3. Pick 5 well-known large-cap tickers per sector (manually curated for liquid, backtestable names)
top5 = {
    "Communication Services": ["CSCO", "ANET", "MSI", "FFIV", "UI"],
    "Consumer Discretionary": ["TSLA", "HD", "LOW", "TJX", "NKE"],
    "Consumer Staples": ["KO", "PG", "CL", "KMB", "CLX"],
    "Energy": ["XOM", "CVX", "EOG", "SLB", "HAL"],
    "Financials": ["V", "MA", "SPGI", "MSCI", "DFIN"],
    "Health Care": ["JNJ", "LLY", "ISRG", "BSX", "SYK"],
    "Industrials": ["CMI", "ETN", "EMR", "GWW", "ITW"],
    "Information Technology": ["NVDA", "AAPL", "AVGO", "CRM", "ADBE"],
    "Materials": ["LIN", "SHW", "NUE", "PPG", "ECL"],
    "Real Estate": ["EQIX", "WELL", "ELS", "RYN", "RM"],
    "Utilities": ["CWCO"],  # only 1 ticker available
}

# Validate all picks exist in master
all_tickers = {r["ticker"] for r in cleaned}
for sector, picks in top5.items():
    for t in picks:
        if t not in all_tickers:
            print(f"  WARNING: {t} not in master for {sector}")

OUT_TOP5.write_text(json.dumps(top5, indent=2))
total_test = sum(len(v) for v in top5.items())
print(f"\nTop 5 per sector: {sum(len(v) for v in top5.values())} tickers → {OUT_TOP5}")
for s, tickers in top5.items():
    print(f"  {s}: {tickers}")
