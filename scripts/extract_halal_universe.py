#!/usr/bin/env python3
"""
Extract halal stock universe from stock-analysis-agent Musaffa data
and create modular data files for MyTradingSpace agents.

Primary source: MasterData/tv_import_ALL_HALAL_STOCKS.txt (definitive ticker list)
Metadata source: musaffa_us_halal_stocks_with_exchange.csv (sector, rating, market cap)
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(ROOT))
import paths

AGENT_DIR = ROOT.parent / "Trading" / "stock-analysis-agent"
TV_IMPORT = AGENT_DIR / "MasterData" / "tv_import_ALL_HALAL_STOCKS.txt"
SOURCE_CSV = AGENT_DIR / "musaffa_us_halal_stocks_with_exchange.csv"
OUTPUT_DIR = paths.HALAL_UNIVERSE

# Exchange name mapping: TV format -> CSV format
EXCHANGE_MAP = {"AMEX": "XASE"}


def parse_market_cap_value(cap_str: str) -> float:
    """Convert '$4.57T' / '$304.02B' / '$141.57M' to numeric USD."""
    cap = cap_str.replace("$", "").strip()
    if not cap:
        return 0.0
    if cap.endswith("T"):
        return float(cap[:-1]) * 1e12
    if cap.endswith("B"):
        return float(cap[:-1]) * 1e9
    if cap.endswith("M"):
        return float(cap[:-1]) * 1e6
    return 0.0


def market_cap_tier(cap_str: str) -> str:
    val = parse_market_cap_value(cap_str)
    if val >= 1e12:
        return "mega"
    if val >= 200e9:
        return "mega"
    if val >= 10e9:
        return "large"
    if val >= 2e9:
        return "mid"
    if val >= 300e6:
        return "small"
    if val >= 50e6:
        return "micro"
    return "nano"


def load_tv_tickers() -> list[dict]:
    """Parse tv_import file -> list of {ticker, exchange}."""
    tickers = []
    with open(TV_IMPORT) as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            exchange, ticker = line.split(":", 1)
            tickers.append({"ticker": ticker, "exchange": exchange})
    return tickers


def load_csv_metadata() -> dict:
    """Load CSV into a ticker -> metadata lookup dict."""
    lookup = {}
    with open(SOURCE_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ticker = row["Ticker"]
            if "." in ticker:
                continue
            lookup[ticker] = {
                "name": row["Name"],
                "exchange": row["Exchange"],
                "halal_rating": row["Halal Rating"],
                "sector": row["Sector"] or "N/A",
                "industry": row["Industry"],
                "market_cap": row["Market Cap"],
                "market_cap_usd": parse_market_cap_value(row["Market Cap"]),
                "market_cap_tier": market_cap_tier(row["Market Cap"]),
            }
    return lookup


def load_stocks():
    """Load definitive ticker list from TV import, enrich with CSV metadata."""
    tv_tickers = load_tv_tickers()
    csv_meta = load_csv_metadata()

    stocks = []
    missing = []
    for entry in tv_tickers:
        ticker = entry["ticker"]
        meta = csv_meta.get(ticker)
        if meta:
            stocks.append({"ticker": ticker, **meta})
        else:
            # Ticker in TV file but not in CSV — include with minimal info
            missing.append(ticker)
            stocks.append({
                "ticker": ticker,
                "name": ticker,
                "exchange": entry["exchange"],
                "halal_rating": "?",
                "sector": "N/A",
                "industry": "Unknown",
                "market_cap": "$0",
                "market_cap_usd": 0.0,
                "market_cap_tier": "nano",
            })

    if missing:
        print(f"  ⚠️  {len(missing)} tickers in TV file but not in CSV: {missing[:10]}...")

    return stocks


def build_master(stocks):
    """Build the full master JSON."""
    by_sector = defaultdict(list)
    for s in stocks:
        by_sector[s["sector"]].append(s)

    # Sort each sector by market cap descending
    for sector in by_sector:
        by_sector[sector].sort(key=lambda x: -x["market_cap_usd"])

    sector_summary = {
        k: len(v) for k, v in sorted(by_sector.items(), key=lambda x: -len(x[1]))
    }

    return {
        "metadata": {
            "source": "Musaffa.com",
            "filters": "US-listed, Shariah-compliant (HALAL), excludes non-US ADRs",
            "total_stocks": len(stocks),
            "sectors": sector_summary,
        },
        "stocks_by_sector": {
            sector: [
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "exchange": s["exchange"],
                    "halal_rating": s["halal_rating"],
                    "industry": s["industry"],
                    "market_cap": s["market_cap"],
                    "market_cap_tier": s["market_cap_tier"],
                }
                for s in sector_stocks
            ]
            for sector, sector_stocks in sorted(
                by_sector.items(), key=lambda x: -len(x[1])
            )
        },
    }


def build_sector_tickers(stocks):
    """Build sector -> ticker lists (sorted by market cap desc)."""
    by_sector = defaultdict(list)
    for s in stocks:
        by_sector[s["sector"]].append(s)

    result = {}
    for sector in sorted(by_sector):
        by_sector[sector].sort(key=lambda x: -x["market_cap_usd"])
        result[sector] = [s["ticker"] for s in by_sector[sector]]
    return result


def build_top_tickers_by_sector(stocks, top_n=10):
    """Top N tickers per sector by market cap — for backtest universe."""
    sector_tickers = build_sector_tickers(stocks)
    return {sector: tickers[:top_n] for sector, tickers in sector_tickers.items()}


def main():
    print(f"Reading tickers from: {TV_IMPORT}")
    print(f"Metadata from: {SOURCE_CSV}")
    stocks = load_stocks()
    print(f"Loaded {len(stocks)} US-listed halal stocks")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Full master JSON
    master = build_master(stocks)
    master_path = OUTPUT_DIR / "halal_master.json"
    with open(master_path, "w") as f:
        json.dump(master, f, indent=2)
    print(f"  -> {master_path} ({master['metadata']['total_stocks']} stocks)")

    # 2. Sector tickers (all)
    sector_tickers = build_sector_tickers(stocks)
    sector_path = OUTPUT_DIR / "halal_sector_tickers.json"
    with open(sector_path, "w") as f:
        json.dump(sector_tickers, f, indent=2)
    print(f"  -> {sector_path} ({len(sector_tickers)} sectors)")

    # 3. Top 10 per sector for backtests
    top10 = build_top_tickers_by_sector(stocks, top_n=10)
    top10_path = OUTPUT_DIR / "halal_top10_by_sector.json"
    with open(top10_path, "w") as f:
        json.dump(top10, f, indent=2)
    print(f"  -> {top10_path}")

    # 4. Flat ticker list (all, sorted by market cap)
    stocks_sorted = sorted(stocks, key=lambda x: -x["market_cap_usd"])
    all_tickers = [s["ticker"] for s in stocks_sorted]
    flat_path = OUTPUT_DIR / "halal_all_tickers.json"
    with open(flat_path, "w") as f:
        json.dump(all_tickers, f, indent=2)
    print(f"  -> {flat_path} ({len(all_tickers)} tickers)")

    # 5. Python module for direct import
    py_path = OUTPUT_DIR / "__init__.py"
    lines = [
        '"""',
        "Halal stock universe — auto-generated from Musaffa data.",
        f"Total: {len(stocks)} US-listed Shariah-compliant stocks across {len(sector_tickers)} sectors.",
        '"""',
        "",
        "import json",
        "from pathlib import Path",
        "",
        "_DIR = Path(__file__).parent",
        "",
        "",
        "def load_master():",
        '    """Full master data with metadata, all stocks by sector."""',
        '    with open(_DIR / "halal_master.json") as f:',
        "        return json.load(f)",
        "",
        "",
        "def load_sector_tickers():",
        '    """Dict[sector, List[ticker]] — all halal tickers grouped by sector."""',
        '    with open(_DIR / "halal_sector_tickers.json") as f:',
        "        return json.load(f)",
        "",
        "",
        "def load_top_tickers(n=10):",
        '    """Top N tickers per sector by market cap — for backtest universe."""',
        '    all_sectors = load_sector_tickers()',
        "    return {sector: tickers[:n] for sector, tickers in all_sectors.items()}",
        "",
        "",
        "def load_all_tickers():",
        '    """Flat list of all halal tickers, sorted by market cap desc."""',
        '    with open(_DIR / "halal_all_tickers.json") as f:',
        "        return json.load(f)",
        "",
        "",
        "# Pre-built sector dict matching backtests/common.py format",
        "HALAL_SECTORS = " + json.dumps(top10, indent=4),
        "",
        "HALAL_ALL_TICKERS = " + json.dumps(all_tickers[:50]),
        "",
    ]
    with open(py_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  -> {py_path}")

    # Summary
    print("\n" + "=" * 60)
    print("SECTOR SUMMARY")
    print("=" * 60)
    for sector, tickers in sorted(sector_tickers.items(), key=lambda x: -len(x[1])):
        print(f"  {sector:30s} {len(tickers):4d} tickers  (top 5: {', '.join(tickers[:5])})")
    print(f"\n  TOTAL: {len(stocks)} halal stocks")

    # Flag any non-halal tickers in current backtest universe
    halal_set = set(all_tickers)
    current_universe = {
        "Technology": ["AAPL","MSFT","NVDA","GOOGL","META","AMZN","TSLA","ORCL","ANET","CRM"],
        "Healthcare": ["JNJ","UNH","LLY","ABBV","MRK","PFE","BMY","CVS","CI","ABT"],
        "Financials": ["JPM","BAC","WFC","GS","MS","V","MA","AXP","BLK","C"],
        "Consumer_Staples": ["PEP","KO","PG","WMT","COST","MCD","PM","MO","GIS","CL"],
        "Energy": ["XOM","CVX","COP","SLB","OXY","PSX","VLO","MPC","EOG","HAL"],
    }
    print("\n" + "=" * 60)
    print("CURRENT BACKTEST UNIVERSE vs HALAL COMPLIANCE")
    print("=" * 60)
    for sector, tickers in current_universe.items():
        non_halal = [t for t in tickers if t not in halal_set]
        status = "✅ ALL HALAL" if not non_halal else f"⚠️  NON-HALAL: {non_halal}"
        print(f"  {sector:20s} {status}")


if __name__ == "__main__":
    main()
