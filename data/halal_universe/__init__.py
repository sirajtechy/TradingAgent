"""
Halal stock universe — auto-generated from Musaffa data.
Total: 1236 US-listed Shariah-compliant stocks across 12 sectors.
"""

import json
from pathlib import Path

_DIR = Path(__file__).parent


def load_master():
    """Full master data with metadata, all stocks by sector."""
    with open(_DIR / "halal_master.json") as f:
        return json.load(f)


def load_sector_tickers():
    """Dict[sector, List[ticker]] — all halal tickers grouped by sector."""
    with open(_DIR / "halal_sector_tickers.json") as f:
        return json.load(f)


def load_top_tickers(n=10):
    """Top N tickers per sector by market cap — for backtest universe."""
    all_sectors = load_sector_tickers()
    return {sector: tickers[:n] for sector, tickers in all_sectors.items()}


def load_all_tickers():
    """Flat list of all halal tickers, sorted by market cap desc."""
    with open(_DIR / "halal_all_tickers.json") as f:
        return json.load(f)


# Pre-built sector dict matching backtests/common.py format
HALAL_SECTORS = {
    "Communication Services": [
        "CSCO",
        "ANET",
        "MSI",
        "RBLX",
        "UI",
        "CIEN",
        "TTD",
        "FFIV",
        "CARG",
        "CALX"
    ],
    "Consumer Discretionary": [
        "TSLA",
        "HD",
        "TJX",
        "DASH",
        "SBUX",
        "NKE",
        "ORLY",
        "ROST",
        "AZO",
        "CPNG"
    ],
    "Consumer Staples": [
        "PG",
        "MNST",
        "CL",
        "DHI",
        "GRMN",
        "EL",
        "HSY",
        "KMB",
        "KVUE",
        "ADM"
    ],
    "Energy": [
        "XOM",
        "CVX",
        "EOG",
        "SLB",
        "VLO",
        "BKR",
        "CCJ",
        "EXE",
        "HAL",
        "DVN"
    ],
    "Financials": [
        "V",
        "MA",
        "SPGI",
        "MCO",
        "MSCI",
        "BLSH",
        "DLO",
        "PAY",
        "RELY",
        "FLYW"
    ],
    "Health Care": [
        "LLY",
        "JNJ",
        "MRK",
        "TMO",
        "ABT",
        "ISRG",
        "DHR",
        "GILD",
        "BSX",
        "SYK"
    ],
    "Industrials": [
        "GEV",
        "APH",
        "UNP",
        "ETN",
        "PH",
        "WM",
        "TT",
        "MMM",
        "UPS",
        "CTAS"
    ],
    "Information Technology": [
        "NVDA",
        "AAPL",
        "AVGO",
        "ORCL",
        "AMD",
        "MU",
        "CRM",
        "LRCX",
        "AMAT",
        "QCOM"
    ],
    "Materials": [
        "LIN",
        "SHW",
        "ECL",
        "APD",
        "CTVA",
        "NUE",
        "STLD",
        "PPG",
        "PKG",
        "DD"
    ],
    "N/A": [
        "RAL WI",
        "APXT",
        "VACI",
        "TDWD",
        "SMJF",
        "Q WI"
    ],
    "Real Estate": [
        "WELL",
        "EQIX",
        "CSGP",
        "WY",
        "ELS",
        "TRNO",
        "COMP",
        "MRP WI",
        "LB",
        "RYN"
    ],
    "Utilities": [
        "MGEE",
        "HNRG",
        "CDZI",
        "MNTK",
        "ANNA"
    ]
}

HALAL_ALL_TICKERS = ["NVDA", "AAPL", "AVGO", "TSLA", "LLY", "V", "ORCL", "MA", "JNJ", "XOM", "AMD", "HD", "PG", "MU", "CSCO", "CVX", "MRK", "CRM", "LRCX", "TMO", "ABT", "AMAT", "ISRG", "LIN", "QCOM", "GEV", "TJX", "ANET", "APH", "KLAC", "DHR", "SPGI", "NOW", "TXN", "GILD", "ADBE", "BSX", "UNP", "SYK", "PANW", "WELL", "ETN", "MDT", "CRWD", "ARM", "VRTX", "PH", "MCK", "DASH", "SBUX"]
