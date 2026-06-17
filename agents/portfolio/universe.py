"""Halal universe loading and sector mapping."""

from __future__ import annotations

from typing import Dict, List, Tuple

from data.halal_universe import HALAL_SECTORS, load_all_tickers, load_sector_tickers, load_top_tickers


def load_universe(mode: str = "top10", top_n: int = 10) -> Tuple[List[str], Dict[str, str]]:
    """
    Return (tickers, ticker_to_sector).

    ``mode``:
      - ``top10``: top N by sector (default pilot / fast backtest)
      - ``full``: all halal tickers from sector JSON
    """
    ticker_to_sector: Dict[str, str] = {}

    if mode == "full":
        sectors = load_sector_tickers()
        tickers: List[str] = []
        for sector, names in sectors.items():
            for t in names:
                sym = str(t).strip().upper()
                if not sym or " " in sym:
                    continue
                tickers.append(sym)
                ticker_to_sector[sym] = sector
        return sorted(set(tickers)), ticker_to_sector

    if mode == "top10":
        sectors = load_top_tickers(top_n)
        tickers = []
        for sector, names in sectors.items():
            for t in names:
                sym = str(t).strip().upper()
                if not sym or " " in sym:
                    continue
                tickers.append(sym)
                ticker_to_sector[sym] = sector
        return sorted(set(tickers)), ticker_to_sector

    # fallback: flat all list capped
    all_list = load_all_tickers()
    sectors_full = load_sector_tickers()
    flat_sector: Dict[str, str] = {}
    for sector, names in sectors_full.items():
        for t in names:
            flat_sector[str(t).strip().upper()] = sector
    capped = [str(t).strip().upper() for t in all_list[: max(top_n * 12, 120)]]
    for sym in capped:
        ticker_to_sector[sym] = flat_sector.get(sym, "Unknown")
    return capped, ticker_to_sector


def exit_rank_threshold(universe_size: int, exit_rank_pct: float) -> int:
    """Rank above which a holding is removed (FRR exit)."""
    if universe_size <= 0:
        return 1
    threshold = max(int(universe_size * exit_rank_pct), 1)
    return threshold
