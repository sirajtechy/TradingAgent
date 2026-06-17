"""Event-driven portfolio simulation."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from agents.portfolio.config import PortfolioRules
from agents.portfolio.data_provider import PriceDataProvider
from agents.portfolio.metrics import build_summary, monthly_returns_from_curve
from agents.portfolio.models import BacktestResult, Holding, PortfolioSnapshot, TradeRecord
from agents.portfolio.rebalancer import frr_actions, rebalance_dates
from agents.portfolio.regime import is_bull_regime
from agents.portfolio.scorer import rank_universe
from agents.portfolio.selector import select_portfolio
from agents.portfolio.sizer import shares_from_allocation, size_positions
from agents.portfolio.universe import exit_rank_threshold, load_universe


def _liquidate_all(
    holdings: Dict[str, Holding],
    prices: Dict[str, float],
    as_of: date,
    reason: str,
) -> tuple[float, List[TradeRecord]]:
    cash = 0.0
    trades: List[TradeRecord] = []
    for sym, h in list(holdings.items()):
        px = prices.get(sym)
        if px is None or px <= 0:
            continue
        proceeds = h.shares * px
        cash += proceeds
        trades.append(
            TradeRecord(
                date=as_of,
                action="SELL",
                ticker=sym,
                sector=h.sector,
                shares=h.shares,
                price=px,
                proceeds=round(proceeds, 2),
                rank=None,
                conviction=None,
                reason=reason,
            )
        )
        del holdings[sym]
    return cash, trades


def run_simulation(
    *,
    start: date,
    end: date,
    rules: PortfolioRules,
    provider: PriceDataProvider,
    enrich_fn=None,
    warnings: Optional[List[str]] = None,
) -> BacktestResult:
    warnings = warnings or []
    run_id = f"portfolio_{start.isoformat()}_{end.isoformat()}_{uuid.uuid4().hex[:8]}"
    tickers, ticker_to_sector = load_universe(rules.universe_mode)
    exit_rank = exit_rank_threshold(len(tickers), rules.exit_rank_pct)

    if not provider.available:
        warnings.append("POLYGON_API_KEY missing — backtest uses empty price panel.")

    cash = float(rules.budget)
    holdings: Dict[str, Holding] = {}
    trades: List[TradeRecord] = []
    equity_curve: List[Dict[str, Any]] = []
    snapshots: List[PortfolioSnapshot] = []
    regime_cash_count = 0

    dates = rebalance_dates(start, end, rules.rebalance_day)

    for rb_date in dates:
        spy_weekly = provider.get_weekly(rules.regime_index, rb_date) if rules.regime_enabled else None
        bull = is_bull_regime(
            spy_weekly,
            period=rules.supertrend_period,
            multiplier=rules.supertrend_multiplier,
        ) if rules.regime_enabled else True

        price_data = provider.batch_daily(tickers, rb_date)
        spy_daily = price_data.get(rules.regime_index) or provider.get_daily(rules.regime_index, rb_date)

        enrich = enrich_fn(tickers, rb_date.isoformat()) if enrich_fn else None
        ranked = rank_universe(
            price_data=price_data,
            spy_df=spy_daily,
            ticker_to_sector=ticker_to_sector,
            rules=rules,
            agent_enrichment=enrich,
            as_of=rb_date,
        )

        prices = {sym: float(df["Close"].iloc[-1]) for sym, df in price_data.items() if not df.empty}

        if not bull:
            regime_cash_count += 1
            cash_added, sell_trades = _liquidate_all(holdings, prices, rb_date, "regime_bear_cash")
            cash += cash_added
            trades.extend(sell_trades)
            equity_curve.append({"as_of": rb_date, "total_value": round(cash, 2), "regime": "bear_cash"})
            snapshots.append(
                PortfolioSnapshot(
                    as_of=rb_date,
                    cash=round(cash, 2),
                    equity_value=0.0,
                    total_value=round(cash, 2),
                    holdings=[],
                    regime="bear_cash",
                )
            )
            continue

        to_remove, to_hold, replacements = frr_actions(
            holdings,
            ranked,
            exit_rank=exit_rank,
            num_stocks=rules.num_stocks,
        )

        for sym in to_remove:
            h = holdings.pop(sym, None)
            if h is None:
                continue
            px = prices.get(sym, h.entry_price)
            proceeds = h.shares * px
            cash += proceeds
            row = next((r for r in ranked if r.ticker == sym), None)
            trades.append(
                TradeRecord(
                    date=rb_date,
                    action="SELL",
                    ticker=sym,
                    sector=h.sector,
                    shares=h.shares,
                    price=px,
                    proceeds=round(proceeds, 2),
                    rank=row.rank if row else None,
                    conviction=row.conviction_score if row else None,
                    reason="frr_exit_rank",
                    attribution=row.attribution if row else {},
                )
            )

        target_names = select_portfolio(
            ranked,
            num_stocks=rules.num_stocks,
            rules=rules,
            existing=set(to_hold),
        )
        allocs = size_positions(target_names, budget=cash + sum(
            holdings[s].shares * prices.get(s, holdings[s].entry_price) for s in holdings
        ), rules=rules)

        # Rebalance buys for new names and top-up equal weight
        portfolio_value = cash + sum(
            holdings[s].shares * prices.get(s, holdings[s].entry_price) for s in holdings
        )
        allocs = size_positions(target_names, budget=portfolio_value, rules=rules)

        for row in target_names:
            sym = row.ticker
            px = prices.get(sym)
            if px is None or px <= 0:
                continue
            target_dollars = allocs.get(sym, 0.0)
            current_value = holdings[sym].shares * px if sym in holdings else 0.0
            delta = target_dollars - current_value
            if delta <= 0 and sym in holdings:
                continue
            buy_dollars = max(delta, 0.0)
            if buy_dollars <= 0 and sym not in holdings:
                buy_dollars = target_dollars
            new_shares = shares_from_allocation(buy_dollars, px)
            if new_shares <= 0:
                continue
            cost = new_shares * px
            if cost > cash:
                new_shares = shares_from_allocation(cash, px)
                cost = new_shares * px
            if new_shares <= 0:
                continue
            cash -= cost
            if sym in holdings:
                h = holdings[sym]
                total_shares = h.shares + new_shares
                h.cost_basis += cost
                h.shares = total_shares
                h.entry_price = h.cost_basis / total_shares if total_shares else px
            else:
                holdings[sym] = Holding(
                    ticker=sym,
                    sector=row.sector,
                    shares=float(new_shares),
                    entry_date=rb_date,
                    entry_price=px,
                    cost_basis=cost,
                    rank_at_entry=row.rank,
                    conviction_at_entry=row.conviction_score,
                )
            trades.append(
                TradeRecord(
                    date=rb_date,
                    action="BUY",
                    ticker=sym,
                    sector=row.sector,
                    shares=float(new_shares),
                    price=px,
                    proceeds=round(-cost, 2),
                    rank=row.rank,
                    conviction=row.conviction_score,
                    reason="frr_replace" if sym not in to_hold else "rebalance_hold",
                    attribution=row.attribution,
                )
            )

        equity_value = sum(holdings[s].shares * prices.get(s, h.entry_price) for s, h in holdings.items())
        total = cash + equity_value
        equity_curve.append({"as_of": rb_date, "total_value": round(total, 2), "regime": "bull"})
        snapshots.append(
            PortfolioSnapshot(
                as_of=rb_date,
                cash=round(cash, 2),
                equity_value=round(equity_value, 2),
                total_value=round(total, 2),
                holdings=[
                    {
                        "ticker": h.ticker,
                        "sector": h.sector,
                        "shares": h.shares,
                        "value": round(h.shares * prices.get(h.ticker, h.entry_price), 2),
                        "rank_at_entry": h.rank_at_entry,
                        "conviction_at_entry": h.conviction_at_entry,
                    }
                    for h in holdings.values()
                ],
                regime="bull",
            )
        )

    final_value = equity_curve[-1]["total_value"] if equity_curve else cash
    summary = build_summary(
        initial=rules.budget,
        final=final_value,
        start=start,
        end=end,
        equity_curve=equity_curve,
        trade_count=len(trades),
        regime_cash_months=regime_cash_count,
    )

    return BacktestResult(
        run_id=run_id,
        start_date=start,
        end_date=end,
        initial_budget=rules.budget,
        final_value=final_value,
        total_return_pct=summary.get("total_return_pct") or 0.0,
        cagr_pct=summary.get("cagr_pct"),
        max_drawdown_pct=summary.get("max_drawdown_pct") or 0.0,
        sharpe_ratio=summary.get("sharpe_ratio"),
        monthly_returns=monthly_returns_from_curve(equity_curve),
        equity_curve=equity_curve,
        trades=trades,
        snapshots=snapshots,
        summary=summary,
        warnings=warnings,
    )
