"""Public portfolio API — backtest and live allocation."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.portfolio.config import PortfolioRules, load_rules
from agents.portfolio.data_provider import PriceDataProvider
from agents.portfolio.enrich import enrich_top_candidates
from agents.portfolio.sector_report import sector_theme_report
from agents.portfolio.models import BacktestResult
from agents.portfolio.scorer import rank_universe
from agents.portfolio.selector import select_portfolio
from agents.portfolio.sizer import shares_from_allocation, size_positions
from agents.portfolio.simulator import run_simulation
from agents.portfolio.universe import load_universe

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = ROOT / "data" / "output" / "portfolio_backtests"


def _parse_date(s: str) -> date:
    return date.fromisoformat(s[:10])


def _result_to_dict(result: BacktestResult) -> Dict[str, Any]:
    return {
        "run_id": result.run_id,
        "start_date": result.start_date.isoformat(),
        "end_date": result.end_date.isoformat(),
        "summary": result.summary,
        "warnings": result.warnings,
        "monthly_returns": result.monthly_returns,
        "equity_curve": [
            {**pt, "as_of": pt["as_of"].isoformat() if hasattr(pt.get("as_of"), "isoformat") else pt.get("as_of")}
            for pt in result.equity_curve
        ],
        "trade_count": len(result.trades),
    }


def write_backtest_outputs(result: BacktestResult, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or (OUTPUT_ROOT / result.run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    sector = sector_theme_report(result.trades)
    payload = _result_to_dict(result)
    payload["sector_themes"] = sector

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    monthly_path = out_dir / "monthly_returns.csv"
    with monthly_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["month", "portfolio_value", "return_pct"])
        w.writeheader()
        for row in result.monthly_returns:
            w.writerow(row)

    trades_path = out_dir / "trade_history.csv"
    with trades_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "action",
                "ticker",
                "sector",
                "shares",
                "price",
                "proceeds",
                "rank",
                "conviction",
                "reason",
            ],
        )
        w.writeheader()
        for t in result.trades:
            w.writerow(
                {
                    "date": t.date.isoformat(),
                    "action": t.action,
                    "ticker": t.ticker,
                    "sector": t.sector,
                    "shares": t.shares,
                    "price": round(t.price, 4),
                    "proceeds": t.proceeds,
                    "rank": t.rank,
                    "conviction": t.conviction,
                    "reason": t.reason,
                }
            )

    if result.snapshots:
        last = result.snapshots[-1]
        holdings_path = out_dir / f"holdings_{last.as_of.isoformat()}.json"
        holdings_path.write_text(
            json.dumps(
                {
                    "as_of": last.as_of.isoformat(),
                    "cash": last.cash,
                    "equity_value": last.equity_value,
                    "total_value": last.total_value,
                    "regime": last.regime,
                    "holdings": last.holdings,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return out_dir


def _default_enrich_max(*, full_agents: bool, enrich_max: Optional[int]) -> int:
    if enrich_max is not None:
        return enrich_max
    return 10 if full_agents else 30


def backtest_portfolio(
    *,
    start: str,
    end: str,
    budget: float = 200_000.0,
    universe_mode: str = "top10",
    num_stocks: int = 20,
    enrich_agents: bool = False,
    full_agents: bool = False,
    strategy_profile: str = "blend",
    enrich_max: Optional[int] = None,
    enrich_workers: int = 8,
    write_outputs: bool = True,
) -> BacktestResult:
    rules = load_rules(
        overrides={
            "budget_default": budget,
            "universe_mode_default": universe_mode,
            "num_stocks": num_stocks,
        }
    )
    rules.budget = budget
    rules.universe_mode = universe_mode
    rules.num_stocks = num_stocks

    provider = PriceDataProvider()
    warnings: List[str] = []

    enrich_fn = None
    if enrich_agents or full_agents:
        tickers, _ = load_universe(universe_mode)

        enrich_cap = _default_enrich_max(full_agents=full_agents, enrich_max=enrich_max)

        def enrich_fn(symbols, as_of_date):  # type: ignore
            top = symbols[: min(50, len(symbols))]
            return enrich_top_candidates(
                top,
                as_of_date,
                strategy_profile=strategy_profile,
                max_tickers=enrich_cap,
                full_agents=full_agents,
                max_workers=enrich_workers,
            )

    result = run_simulation(
        start=_parse_date(start),
        end=_parse_date(end),
        rules=rules,
        provider=provider,
        enrich_fn=enrich_fn,
        warnings=warnings,
    )

    if write_outputs:
        write_backtest_outputs(result)

    return result


def allocate_portfolio(
    *,
    as_of: str,
    budget: float = 200_000.0,
    universe_mode: str = "top10",
    num_stocks: int = 20,
    enrich_agents: bool = True,
    full_agents: bool = False,
    strategy_profile: str = "blend",
    enrich_max: Optional[int] = None,
    enrich_workers: int = 8,
) -> Dict[str, Any]:
    """Live advisory book for a single rebalance date."""
    rules = load_rules(
        overrides={
            "budget_default": budget,
            "universe_mode_default": universe_mode,
            "num_stocks": num_stocks,
        }
    )
    rules.budget = budget
    rules.universe_mode = universe_mode
    rules.num_stocks = num_stocks

    as_of_date = _parse_date(as_of)
    tickers, ticker_to_sector = load_universe(universe_mode)
    provider = PriceDataProvider()

    price_data = provider.batch_daily(tickers, as_of_date)
    spy_df = price_data.get(rules.regime_index) or provider.get_daily(rules.regime_index, as_of_date)

    enrich = None
    if enrich_agents or full_agents:
        pre_rank = rank_universe(
            price_data=price_data,
            spy_df=spy_df,
            ticker_to_sector=ticker_to_sector,
            rules=rules,
            as_of=as_of_date,
        )
        enrich_cap = _default_enrich_max(full_agents=full_agents, enrich_max=enrich_max)
        top_syms = [r.ticker for r in pre_rank[: min(50, len(pre_rank))]]
        enrich = enrich_top_candidates(
            top_syms,
            as_of,
            strategy_profile=strategy_profile,
            max_tickers=enrich_cap,
            full_agents=full_agents,
            max_workers=enrich_workers,
        )

    ranked = rank_universe(
        price_data=price_data,
        spy_df=spy_df,
        ticker_to_sector=ticker_to_sector,
        rules=rules,
        agent_enrichment=enrich,
        as_of=as_of_date,
    )
    selected = select_portfolio(ranked, num_stocks=num_stocks, rules=rules)
    allocs = size_positions(selected, budget=budget, rules=rules)

    rows: List[Dict[str, Any]] = []
    for row in selected:
        px = None
        df = price_data.get(row.ticker)
        if df is not None and not df.empty:
            px = float(df["Close"].iloc[-1])
        dollars = allocs.get(row.ticker, 0.0)
        shares = shares_from_allocation(dollars, px or 0.0)
        rows.append(
            {
                "ticker": row.ticker,
                "sector": row.sector,
                "rank": row.rank,
                "conviction_score": row.conviction_score,
                "momentum_score": row.momentum_score,
                "allocation_usd": dollars,
                "shares": shares,
                "price": px,
                "attribution": row.attribution,
                "components": row.components,
            }
        )

    out = {
        "schema_version": "1.0",
        "as_of": as_of_date.isoformat(),
        "budget": budget,
        "num_stocks": num_stocks,
        "universe_mode": universe_mode,
        "holdings": rows,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    out_dir = ROOT / "data" / "output" / "portfolio_allocations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"holdings_{as_of_date.isoformat()}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    out["output_path"] = str(out_path.relative_to(ROOT))

    return out
