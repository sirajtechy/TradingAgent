from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .models import DividendEvent, RawFundamentalSnapshot, StatementEntry


PROHIBITED_BUSINESS_KEYWORDS = [
    "alcohol",
    "casino",
    "gambling",
    "pork",
    "tobacco",
    "adult",
    "porn",
    "conventional bank",
    "banks",
    "insurance",
    "weapons",
    "defense",
]
FINANCIAL_SECTOR_KEYWORDS = ["financial", "bank", "insurance", "asset management", "broker"]
UTILITY_SECTOR_KEYWORDS = ["utility", "utilities"]
SHARIAH_STANDARDS = {
    "aaoifi": {
        "label": "AAOIFI 30% market cap",
        "debt_threshold": 0.30,
        "cash_threshold": 0.30,
        "denominator": "market_cap",
    },
    "djim": {
        "label": "DJIM 33.33% market cap",
        "debt_threshold": 0.3333,
        "cash_threshold": 0.3333,
        "denominator": "market_cap",
    },
    "sc_malaysia": {
        "label": "SC Malaysia 33% total assets",
        "debt_threshold": 0.33,
        "cash_threshold": 0.33,
        "denominator": "total_assets",
    },
}


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def pct_change(current: Optional[float], prior: Optional[float]) -> Optional[float]:
    if current is None or prior in (None, 0):
        return None
    return ((current - prior) / abs(prior)) * 100.0


def average(values: List[Optional[float]]) -> Optional[float]:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return sum(clean_values) / len(clean_values)


def bucket_score(value: Optional[float], ranges: List[Tuple[float, float]]) -> Optional[float]:
    if value is None:
        return None
    for ceiling, score in ranges:
        if value < ceiling:
            return score
    return ranges[-1][1]


def first_value(entry: Optional[StatementEntry], *keys: str) -> Optional[float]:
    if entry is None:
        return None
    return entry.number(*keys)


def shares_outstanding(entry: Optional[StatementEntry]) -> Optional[float]:
    return first_value(entry, "weightedAverageShsOutDil", "weightedAverageShsOut")


def gross_profit(entry: Optional[StatementEntry]) -> Optional[float]:
    value = first_value(entry, "grossProfit")
    if value is not None:
        return value
    revenue = first_value(entry, "revenue")
    cost_of_revenue = first_value(entry, "costOfRevenue")
    if revenue is None or cost_of_revenue is None:
        return None
    return revenue - cost_of_revenue


def operating_cash_flow(entry: Optional[StatementEntry]) -> Optional[float]:
    return first_value(entry, "operatingCashFlow", "netCashProvidedByOperatingActivities")


def dividend_total_last_12_months(dividends: List[DividendEvent], as_of_date: date) -> float:
    total = 0.0
    for event in dividends:
        age_days = (as_of_date - event.event_date).days
        if 0 <= age_days <= 365:
            total += event.dividend
    return total


def dividend_streak_years(dividends: List[DividendEvent], as_of_date: date) -> int:
    years_with_dividends = {event.event_date.year for event in dividends if event.event_date <= as_of_date}
    if not years_with_dividends:
        return 0
    if as_of_date.year in years_with_dividends:
        current_year = as_of_date.year
    else:
        current_year = as_of_date.year - 1
    streak = 0
    while current_year in years_with_dividends:
        streak += 1
        current_year -= 1
    return streak


def _compute_ttm_ebit(snapshot: RawFundamentalSnapshot) -> Optional[float]:
    """Sum EBIT from the most recent 4 quarters to get trailing-twelve-month EBIT."""
    quarters = snapshot.quarterly_income
    if not quarters or len(quarters) < 4:
        return None
    total = 0.0
    for q in quarters[:4]:
        val = first_value(q, "ebit", "operatingIncome")
        if val is None:
            return None
        total += val
    return total


def _eps_momentum_score(snapshot: RawFundamentalSnapshot) -> Optional[float]:
    """Score quarterly EPS acceleration: Q/Q improvement trend over recent quarters."""
    quarters = snapshot.quarterly_income
    if not quarters or len(quarters) < 3:
        return None
    eps_values = []
    for q in quarters[:6]:  # up to 6 quarters
        val = first_value(q, "epsDiluted", "eps")
        if val is None:
            break
        eps_values.append(val)
    if len(eps_values) < 3:
        return None
    # Count how many consecutive quarters show Q/Q EPS improvement (newest first)
    improving = 0
    for i in range(len(eps_values) - 1):
        if eps_values[i] > eps_values[i + 1]:
            improving += 1
        else:
            break
    if improving >= 4:
        return 100.0
    if improving >= 3:
        return 80.0
    if improving >= 2:
        return 60.0
    if improving >= 1:
        return 40.0
    return 20.0


def _fcf_quality_score(snapshot: RawFundamentalSnapshot) -> Optional[float]:
    """Score free-cash-flow quality: FCF margin and FCF yield."""
    current_cash = snapshot.cashflow_statements[0] if snapshot.cashflow_statements else None
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    if not current_cash or not current_income:
        return None
    ocf = operating_cash_flow(current_cash)
    capex = first_value(current_cash, "capitalExpenditure")
    if ocf is None:
        return None
    # capex is often reported as negative in yfinance; take absolute value
    capex_abs = abs(capex) if capex is not None else 0.0
    fcf = ocf - capex_abs
    revenue = first_value(current_income, "revenue")
    fcf_margin = safe_div(fcf, revenue)
    fcf_margin_pct = None if fcf_margin is None else fcf_margin * 100.0
    market_cap = compute_market_cap(snapshot)
    fcf_yield = safe_div(fcf, market_cap)
    fcf_yield_pct = None if fcf_yield is None else fcf_yield * 100.0
    margin_score = bucket_score(
        fcf_margin_pct,
        [(0.0, 15.0), (5.0, 35.0), (10.0, 55.0), (20.0, 75.0), (float("inf"), 100.0)],
    )
    yield_score = bucket_score(
        fcf_yield_pct,
        [(0.0, 15.0), (2.0, 35.0), (5.0, 55.0), (8.0, 75.0), (float("inf"), 100.0)],
    )
    return average([margin_score, yield_score])


def evaluate_snapshot(snapshot: RawFundamentalSnapshot, include_experimental_score: bool = True) -> Dict[str, Any]:
    piotroski = evaluate_piotroski(snapshot)
    altman = evaluate_altman(snapshot)
    graham = evaluate_graham(snapshot)
    greenblatt = evaluate_greenblatt(snapshot)
    lynch = evaluate_lynch(snapshot)
    growth_profile = evaluate_growth_profile(snapshot)
    shariah = evaluate_shariah(snapshot)

    result: Dict[str, Any] = {
        "request": {
            "ticker": snapshot.request.ticker,
            "as_of_date": snapshot.request.as_of_date.isoformat(),
            "shariah_standard": snapshot.request.shariah_standard,
        },
        "company": {
            "ticker": snapshot.profile.ticker,
            "company_name": snapshot.profile.company_name,
            "sector": snapshot.profile.sector,
            "industry": snapshot.profile.industry,
        },
        "as_of_price": {
            "price": round(snapshot.price_point.price, 4),
            "price_date": snapshot.price_point.price_date.isoformat(),
        },
        "data_quality": build_data_quality(snapshot, [piotroski, altman, graham, greenblatt, lynch, growth_profile]),
        "snapshot": build_snapshot_view(snapshot),
        "frameworks": {
            "piotroski": piotroski,
            "altman": altman,
            "graham": graham,
            "greenblatt": greenblatt,
            "lynch": lynch,
            "growth_profile": growth_profile,
            "shariah": shariah,
        },
        "warnings": list(snapshot.warnings),
    }

    if include_experimental_score:
        eps_momentum = _eps_momentum_score(snapshot)
        fcf_quality = _fcf_quality_score(snapshot)
        result["experimental_score"] = build_experimental_score(
            piotroski=piotroski,
            altman=altman,
            graham=graham,
            greenblatt=greenblatt,
            lynch=lynch,
            growth_profile=growth_profile,
            eps_momentum=eps_momentum,
            fcf_quality=fcf_quality,
        )
    return result


def build_snapshot_view(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    income_current = snapshot.income_statements[0] if snapshot.income_statements else None
    income_prior = snapshot.income_statements[1] if len(snapshot.income_statements) > 1 else None
    balance_current = snapshot.balance_statements[0] if snapshot.balance_statements else None
    balance_prior = snapshot.balance_statements[1] if len(snapshot.balance_statements) > 1 else None
    cash_current = snapshot.cashflow_statements[0] if snapshot.cashflow_statements else None

    return {
        "market_cap_proxy": round(compute_market_cap(snapshot), 2) if compute_market_cap(snapshot) is not None else None,
        "revenue_current": first_value(income_current, "revenue"),
        "revenue_prior": first_value(income_prior, "revenue"),
        "eps_current": first_value(income_current, "epsDiluted", "eps"),
        "eps_prior": first_value(income_prior, "epsDiluted", "eps"),
        "net_income_current": first_value(income_current, "netIncome"),
        "operating_cash_flow_current": operating_cash_flow(cash_current),
        "total_assets_current": first_value(balance_current, "totalAssets"),
        "total_assets_prior": first_value(balance_prior, "totalAssets"),
        "total_debt_current": first_value(balance_current, "totalDebt"),
        "cash_current": first_value(balance_current, "cashAndCashEquivalents"),
        "dividend_streak_years": dividend_streak_years(snapshot.dividend_events, snapshot.request.as_of_date),
    }


def build_data_quality(snapshot: RawFundamentalSnapshot, frameworks: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverage_count = 0
    for framework in frameworks:
        if framework.get("applicable"):
            coverage_count += 1
    coverage_ratio = coverage_count / max(len(frameworks), 1)

    if coverage_ratio >= 0.85 and len(snapshot.warnings) <= 2:
        quality = "high"
    elif coverage_ratio >= 0.60:
        quality = "medium"
    else:
        quality = "low"

    return {
        "coverage_ratio": round(coverage_ratio, 2),
        "coverage_quality": quality,
        "warnings_count": len(snapshot.warnings),
    }


def compute_market_cap(snapshot: RawFundamentalSnapshot) -> Optional[float]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    diluted_shares = shares_outstanding(current_income)
    return safe_div(snapshot.price_point.price * diluted_shares, 1.0) if diluted_shares is not None else None


def evaluate_piotroski(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    prior_income = snapshot.income_statements[1] if len(snapshot.income_statements) > 1 else None
    current_balance = snapshot.balance_statements[0] if snapshot.balance_statements else None
    prior_balance = snapshot.balance_statements[1] if len(snapshot.balance_statements) > 1 else None
    current_cash = snapshot.cashflow_statements[0] if snapshot.cashflow_statements else None

    criteria: Dict[str, Optional[bool]] = {}

    roa_current = safe_div(first_value(current_income, "netIncome"), first_value(current_balance, "totalAssets"))
    roa_prior = safe_div(first_value(prior_income, "netIncome"), first_value(prior_balance, "totalAssets"))
    criteria["f1_roa_positive"] = None if roa_current is None else roa_current > 0
    ocf_current = operating_cash_flow(current_cash)
    criteria["f2_operating_cash_flow_positive"] = None if ocf_current is None else ocf_current > 0
    criteria["f3_roa_improving"] = None if roa_current is None or roa_prior is None else roa_current > roa_prior
    criteria["f4_quality_of_earnings"] = None if ocf_current is None or first_value(current_income, "netIncome") is None else ocf_current > first_value(current_income, "netIncome")

    leverage_current = safe_div(first_value(current_balance, "longTermDebt"), first_value(current_balance, "totalAssets"))
    leverage_prior = safe_div(first_value(prior_balance, "longTermDebt"), first_value(prior_balance, "totalAssets"))
    criteria["f5_leverage_decreasing"] = None if leverage_current is None or leverage_prior is None else leverage_current < leverage_prior

    current_ratio_current = safe_div(first_value(current_balance, "totalCurrentAssets"), first_value(current_balance, "totalCurrentLiabilities"))
    current_ratio_prior = safe_div(first_value(prior_balance, "totalCurrentAssets"), first_value(prior_balance, "totalCurrentLiabilities"))
    criteria["f6_liquidity_improving"] = None if current_ratio_current is None or current_ratio_prior is None else current_ratio_current > current_ratio_prior

    shares_current = shares_outstanding(current_income)
    shares_prior = shares_outstanding(prior_income)
    criteria["f7_no_dilution"] = None if shares_current is None or shares_prior is None else shares_current <= shares_prior

    gross_margin_current = safe_div(gross_profit(current_income), first_value(current_income, "revenue"))
    gross_margin_prior = safe_div(gross_profit(prior_income), first_value(prior_income, "revenue"))
    criteria["f8_gross_margin_improving"] = None if gross_margin_current is None or gross_margin_prior is None else gross_margin_current > gross_margin_prior

    asset_turnover_current = safe_div(first_value(current_income, "revenue"), first_value(current_balance, "totalAssets"))
    asset_turnover_prior = safe_div(first_value(prior_income, "revenue"), first_value(prior_balance, "totalAssets"))
    criteria["f9_asset_turnover_improving"] = None if asset_turnover_current is None or asset_turnover_prior is None else asset_turnover_current > asset_turnover_prior

    applicable = sum(value is not None for value in criteria.values())
    total = sum(1 for value in criteria.values() if value)

    return {
        "applicable": applicable > 0,
        "score": total,
        "max_score": applicable,
        "score_pct": round((total / applicable) * 100, 1) if applicable else None,
        "criteria": criteria,
    }


def evaluate_altman(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    current_balance = snapshot.balance_statements[0] if snapshot.balance_statements else None
    if not current_income or not current_balance:
        return {"applicable": False, "notes": ["Insufficient annual statements for Altman Z-Score."]}

    sector_lower = snapshot.profile.sector.lower()
    if any(keyword in sector_lower for keyword in FINANCIAL_SECTOR_KEYWORDS):
        return {"applicable": False, "notes": ["Altman Z-Score is excluded for financial companies."]}

    market_cap = compute_market_cap(snapshot)
    working_capital = None
    current_assets = first_value(current_balance, "totalCurrentAssets")
    current_liabilities = first_value(current_balance, "totalCurrentLiabilities")
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities
    total_assets = first_value(current_balance, "totalAssets")
    retained_earnings = first_value(current_balance, "retainedEarnings")
    ebit = first_value(current_income, "ebit", "operatingIncome")
    total_liabilities = first_value(current_balance, "totalLiabilities")
    revenue = first_value(current_income, "revenue")

    x1 = safe_div(working_capital, total_assets)
    x2 = safe_div(retained_earnings, total_assets)
    x3 = safe_div(ebit, total_assets)
    x4 = safe_div(market_cap, total_liabilities)
    x5 = safe_div(revenue, total_assets)
    components = [x1, x2, x3, x4, x5]
    if any(component is None for component in components):
        return {"applicable": False, "notes": ["Missing one or more Altman Z-Score inputs."]}

    z_score = (1.2 * x1) + (1.4 * x2) + (3.3 * x3) + (0.6 * x4) + x5
    if z_score <= 1.8:
        zone = "distress"
    elif z_score <= 3.0:
        zone = "grey"
    else:
        zone = "safe"

    # v2: capped at 70 for safe zone — Altman detects bankruptcy risk,
    # not investment quality.  Z=3 and Z=15 are both "safe".
    if z_score <= 1.8:
        score_pct = 10.0
    elif z_score <= 3.0:
        score_pct = 30.0 + ((z_score - 1.8) / 1.2) * 25.0   # 30→55
    elif z_score <= 6.0:
        score_pct = 55.0 + ((z_score - 3.0) / 3.0) * 15.0   # 55→70
    else:
        score_pct = 70.0

    notes: List[str] = []
    if not any(keyword in sector_lower for keyword in ["industrial", "basic material", "manufacturing"]):
        notes.append("Altman original model is less reliable outside manufacturing-heavy sectors.")

    return {
        "applicable": True,
        "z_score": round(z_score, 3),
        "zone": zone,
        "score_pct": round(min(score_pct, 100.0), 1),
        "market_cap_proxy": round(market_cap, 2) if market_cap is not None else None,
        "components": {
            "x1_working_capital_to_assets": round(x1, 4),
            "x2_retained_earnings_to_assets": round(x2, 4),
            "x3_ebit_to_assets": round(x3, 4),
            "x4_market_value_equity_to_liabilities": round(x4, 4),
            "x5_sales_to_assets": round(x5, 4),
        },
        "notes": notes,
    }


def evaluate_graham(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    current_balance = snapshot.balance_statements[0] if snapshot.balance_statements else None
    if not current_income or not current_balance:
        return {"applicable": False, "notes": ["Insufficient annual statements for Graham criteria."]}

    criteria: Dict[str, Optional[bool]] = {}
    notes: List[str] = []

    revenue_current = first_value(current_income, "revenue")
    criteria["g1_size"] = None if revenue_current is None else revenue_current >= 500_000_000

    current_ratio = safe_div(first_value(current_balance, "totalCurrentAssets"), first_value(current_balance, "totalCurrentLiabilities"))
    criteria["g2a_current_ratio"] = None if current_ratio is None else current_ratio >= 2.0

    net_current_assets = None
    current_assets = first_value(current_balance, "totalCurrentAssets")
    current_liabilities = first_value(current_balance, "totalCurrentLiabilities")
    if current_assets is not None and current_liabilities is not None:
        net_current_assets = current_assets - current_liabilities
    long_term_debt = first_value(current_balance, "longTermDebt")
    criteria["g2b_long_term_debt_vs_net_current_assets"] = None if net_current_assets is None or long_term_debt is None else long_term_debt <= net_current_assets

    recent_ten = snapshot.income_statements[:10]
    if len(recent_ten) >= 10:
        eps_last_ten = [first_value(entry, "epsDiluted", "eps") for entry in recent_ten]
        criteria["g3_earnings_stability"] = all(value is not None and value > 0 for value in eps_last_ten)
    else:
        criteria["g3_earnings_stability"] = None
        notes.append("Less than ten annual statements are available for Graham earnings stability.")

    streak_years = dividend_streak_years(snapshot.dividend_events, snapshot.request.as_of_date)
    criteria["g4_dividend_record"] = streak_years >= 20 if snapshot.dividend_events else None
    if not snapshot.dividend_events:
        notes.append("No dividend history was available for Graham dividend continuity.")

    if len(recent_ten) >= 10:
        newest_three = [first_value(entry, "epsDiluted", "eps") for entry in recent_ten[:3]]
        oldest_three = [first_value(entry, "epsDiluted", "eps") for entry in recent_ten[-3:]]
        newest_three = [value for value in newest_three if value is not None and value > 0]
        oldest_three = [value for value in oldest_three if value is not None and value > 0]
        if len(newest_three) >= 2 and len(oldest_three) >= 2:
            avg_newest = sum(newest_three) / len(newest_three)
            avg_oldest = sum(oldest_three) / len(oldest_three)
            growth_pct = pct_change(avg_newest, avg_oldest)
            criteria["g5_eps_growth_10y"] = None if growth_pct is None else growth_pct >= 33.0
        else:
            criteria["g5_eps_growth_10y"] = None
    else:
        criteria["g5_eps_growth_10y"] = None

    latest_three_eps = [first_value(entry, "epsDiluted", "eps") for entry in snapshot.income_statements[:3]]
    latest_three_eps = [value for value in latest_three_eps if value is not None and value > 0]
    if latest_three_eps:
        average_eps = sum(latest_three_eps) / len(latest_three_eps)
        pe_average = safe_div(snapshot.price_point.price, average_eps)
        criteria["g6_pe"] = None if pe_average is None else pe_average <= 15.0
    else:
        pe_average = None
        criteria["g6_pe"] = None

    equity = first_value(current_balance, "totalStockholdersEquity", "totalEquity")
    shares = shares_outstanding(current_income)
    book_value_per_share = safe_div(equity, shares)
    pb_ratio = safe_div(snapshot.price_point.price, book_value_per_share)
    if pb_ratio is None or book_value_per_share is None or book_value_per_share <= 0:
        criteria["g7_pb_or_combined_multiplier"] = False
        notes.append("Book value per share is non-positive or unavailable, so Graham P/B fails by design.")
    else:
        pe_value = safe_div(snapshot.price_point.price, first_value(current_income, "epsDiluted", "eps"))
        pe_times_pb = None if pe_value is None else pe_value * pb_ratio
        criteria["g7_pb_or_combined_multiplier"] = pb_ratio <= 1.5 or (pe_times_pb is not None and pe_times_pb <= 22.5)

    applicable_count = sum(value is not None for value in criteria.values())
    passes = sum(1 for value in criteria.values() if value)

    return {
        "applicable": applicable_count > 0,
        "passes": passes,
        "applicable_rules": applicable_count,
        "score_pct": round((passes / applicable_count) * 100, 1) if applicable_count else None,
        "dividend_streak_years": streak_years,
        "criteria": criteria,
        "notes": notes,
    }


def evaluate_greenblatt(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    sector_lower = snapshot.profile.sector.lower()
    if any(keyword in sector_lower for keyword in FINANCIAL_SECTOR_KEYWORDS + UTILITY_SECTOR_KEYWORDS):
        return {
            "applicable": False,
            "notes": ["Greenblatt Magic Formula is excluded for financial and utility sectors."],
        }

    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    current_balance = snapshot.balance_statements[0] if snapshot.balance_statements else None
    if not current_income or not current_balance:
        return {"applicable": False, "notes": ["Insufficient annual statements for Greenblatt metrics."]}

    # v4: Prefer TTM EBIT from quarterly data for more current earnings picture
    ttm_ebit = _compute_ttm_ebit(snapshot)
    ebit = ttm_ebit if ttm_ebit is not None else first_value(current_income, "ebit", "operatingIncome")
    market_cap = compute_market_cap(snapshot)
    total_debt = first_value(current_balance, "totalDebt")
    cash = first_value(current_balance, "cashAndCashEquivalents")
    enterprise_value = None
    if market_cap is not None and total_debt is not None and cash is not None:
        enterprise_value = market_cap + total_debt - cash

    earnings_yield = safe_div(ebit, enterprise_value)
    earnings_yield_pct = None if earnings_yield is None else earnings_yield * 100.0
    # v3: Audit fix 2 — Greenblatt was at fault in 81% of FPs because the old
    # buckets (3/5/8/12%) were too generous, scoring most healthy companies ≥60.
    # Raised thresholds to match Greenblatt's own top-decile guidance (EY>10%).
    ey_score = bucket_score(
        earnings_yield_pct,
        [(3.0, 15.0), (6.0, 35.0), (10.0, 55.0), (15.0, 75.0), (float("inf"), 100.0)],
    )

    ppe_net = first_value(current_balance, "propertyPlantEquipmentNet")
    working_capital = None
    current_assets = first_value(current_balance, "totalCurrentAssets")
    current_liabilities = first_value(current_balance, "totalCurrentLiabilities")
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities
    tangible_capital = None
    if ppe_net is not None and working_capital is not None:
        tangible_capital = ppe_net + working_capital

    roic = safe_div(ebit, tangible_capital)
    roic_pct = None if roic is None else roic * 100.0
    # v3: Audit fix 2 — ROIC buckets raised in tandem with EY buckets.
    roic_score = bucket_score(
        roic_pct,
        [(5.0, 15.0), (12.0, 35.0), (25.0, 55.0), (40.0, 75.0), (float("inf"), 100.0)],
    )

    notes: List[str] = []
    if tangible_capital is not None and tangible_capital <= 0:
        notes.append("Return on capital denominator is non-positive, which makes the metric hard to compare across sectors.")
    if roic_pct is not None and roic_pct > 100.0:
        notes.append("Return on capital is extremely high and should be treated as a capital-light anomaly, not a like-for-like comparison figure.")

    score_pct = average([ey_score, roic_score])
    return {
        "applicable": ey_score is not None or roic_score is not None,
        "earnings_yield_pct": round(earnings_yield_pct, 2) if earnings_yield_pct is not None else None,
        "return_on_capital_pct": round(roic_pct, 2) if roic_pct is not None else None,
        "score_pct": round(score_pct, 1) if score_pct is not None else None,
        "notes": notes,
    }


def evaluate_lynch(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    if not current_income:
        return {"applicable": False, "notes": ["No annual income statement available for Lynch valuation."]}

    current_eps = first_value(current_income, "epsDiluted", "eps")
    if current_eps is None or current_eps <= 0:
        return {"applicable": False, "notes": ["Current EPS is non-positive, so Lynch fair value is not applicable."]}

    available_years = len(snapshot.income_statements)
    if available_years < 2:
        return {"applicable": False, "notes": ["At least two annual statements are required for Lynch EPS CAGR."]}

    # Use the oldest available statement up to 5 years back (index capped at min(available-1, 5)).
    # With 5 statements (indices 0-4) this gives a 4-year CAGR.
    # With 6+ statements (indices 0-5) this gives a 5-year CAGR.
    lookback_index = min(available_years - 1, 5)
    lookback_years = lookback_index  # index == number of years between entry[0] and entry[lookback_index]

    eps_historical = first_value(snapshot.income_statements[lookback_index], "epsDiluted", "eps")
    if eps_historical is None or eps_historical <= 0:
        return {"applicable": False, "notes": ["Historical EPS is unavailable or non-positive for Lynch CAGR."]}

    growth_rate_pct = ((current_eps / eps_historical) ** (1.0 / lookback_years) - 1.0) * 100.0
    trailing_dividend_yield_pct = safe_div(dividend_total_last_12_months(snapshot.dividend_events, snapshot.request.as_of_date), snapshot.price_point.price)
    trailing_dividend_yield_pct = 0.0 if trailing_dividend_yield_pct is None else trailing_dividend_yield_pct * 100.0
    pe_ratio = safe_div(snapshot.price_point.price, current_eps)
    fair_value_ratio = None if pe_ratio is None else (growth_rate_pct + trailing_dividend_yield_pct) / pe_ratio

    score_pct = bucket_score(
        fair_value_ratio,
        [(0.5, 20.0), (1.0, 40.0), (1.5, 60.0), (2.0, 80.0), (float("inf"), 100.0)],
    )

    cagr_label = f"trailing_eps_cagr_{lookback_years}y_pct"
    return {
        "applicable": fair_value_ratio is not None,
        "fair_value_ratio": round(fair_value_ratio, 3) if fair_value_ratio is not None else None,
        "pe_ratio": round(pe_ratio, 2) if pe_ratio is not None else None,
        cagr_label: round(growth_rate_pct, 2),
        "cagr_lookback_years": lookback_years,
        "trailing_dividend_yield_pct": round(trailing_dividend_yield_pct, 2),
        "score_pct": round(score_pct, 1) if score_pct is not None else None,
        "notes": [
            f"Lynch CAGR uses a {lookback_years}-year lookback based on {available_years} available annual statements.",
            "Lynch fair value uses trailing EPS CAGR instead of forward analyst estimates to preserve point-in-time reproducibility.",
        ],
    }


def evaluate_growth_profile(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    prior_income = snapshot.income_statements[1] if len(snapshot.income_statements) > 1 else None
    if not current_income or not prior_income:
        return {"applicable": False, "notes": ["At least two annual income statements are required for the growth profile."]}

    revenue_growth_pct = pct_change(first_value(current_income, "revenue"), first_value(prior_income, "revenue"))
    eps_growth_pct = pct_change(first_value(current_income, "epsDiluted", "eps"), first_value(prior_income, "epsDiluted", "eps"))

    revenue_score = bucket_score(
        revenue_growth_pct,
        [(0.0, 20.0), (5.0, 40.0), (15.0, 60.0), (25.0, 80.0), (float("inf"), 100.0)],
    )
    eps_score = bucket_score(
        eps_growth_pct,
        [(0.0, 20.0), (10.0, 40.0), (20.0, 60.0), (30.0, 80.0), (float("inf"), 100.0)],
    )

    graham_growth_bonus = None
    graham = evaluate_graham(snapshot)
    if graham.get("applicable"):
        graham_growth_bonus = 100.0 if graham.get("criteria", {}).get("g5_eps_growth_10y") else 20.0

    score_pct = average([revenue_score, eps_score, graham_growth_bonus])
    return {
        "applicable": score_pct is not None,
        "revenue_growth_yoy_pct": round(revenue_growth_pct, 2) if revenue_growth_pct is not None else None,
        "eps_growth_yoy_pct": round(eps_growth_pct, 2) if eps_growth_pct is not None else None,
        "score_pct": round(score_pct, 1) if score_pct is not None else None,
        "notes": [],
    }


def evaluate_shariah(snapshot: RawFundamentalSnapshot) -> Dict[str, Any]:
    standard = SHARIAH_STANDARDS.get(snapshot.request.shariah_standard, SHARIAH_STANDARDS["aaoifi"])
    current_income = snapshot.income_statements[0] if snapshot.income_statements else None
    current_balance = snapshot.balance_statements[0] if snapshot.balance_statements else None
    if not current_income or not current_balance:
        return {"applicable": False, "notes": ["Insufficient annual statements for Shariah screening."]}

    sector_text = f"{snapshot.profile.sector} {snapshot.profile.industry}".lower()
    business_screen_pass = not any(keyword in sector_text for keyword in PROHIBITED_BUSINESS_KEYWORDS)

    market_cap = compute_market_cap(snapshot)
    total_assets = first_value(current_balance, "totalAssets")
    denominator = market_cap if standard["denominator"] == "market_cap" else total_assets

    total_debt = first_value(current_balance, "totalDebt")
    cash = first_value(current_balance, "cashAndCashEquivalents")
    short_term_investments = first_value(current_balance, "shortTermInvestments") or 0.0
    revenue = first_value(current_income, "revenue")
    interest_income = first_value(current_income, "interestIncome", "netInterestIncome")

    debt_ratio = safe_div(total_debt, denominator)
    cash_ratio = safe_div((cash or 0.0) + short_term_investments, denominator)
    impure_revenue_proxy_ratio = safe_div(interest_income, revenue)

    notes = [
        "Impure revenue uses interest income as a proxy and should be treated as a partial Shariah screen.",
    ]
    if denominator is None:
        notes.append("The selected denominator was unavailable, so the financial ratio screen is partial.")

    if not business_screen_pass:
        status = "fail"
    elif debt_ratio is None or cash_ratio is None or impure_revenue_proxy_ratio is None:
        status = "partial"
    elif debt_ratio < standard["debt_threshold"] and cash_ratio < standard["cash_threshold"] and impure_revenue_proxy_ratio < 0.05:
        if debt_ratio >= standard["debt_threshold"] * 0.9 or cash_ratio >= standard["cash_threshold"] * 0.9:
            status = "borderline_pass"
        else:
            status = "pass"
    else:
        status = "fail"

    return {
        "applicable": True,
        "standard": standard["label"],
        "status": status,
        "business_screen_pass": business_screen_pass,
        "debt_ratio": round(debt_ratio, 4) if debt_ratio is not None else None,
        "cash_ratio": round(cash_ratio, 4) if cash_ratio is not None else None,
        "impure_revenue_proxy_ratio": round(impure_revenue_proxy_ratio, 5) if impure_revenue_proxy_ratio is not None else None,
        "notes": notes,
    }


def build_experimental_score(
    piotroski: Dict[str, Any],
    altman: Dict[str, Any],
    graham: Dict[str, Any],
    greenblatt: Dict[str, Any],
    lynch: Dict[str, Any],
    growth_profile: Dict[str, Any],
    eps_momentum: Optional[float] = None,
    fcf_quality: Optional[float] = None,
) -> Dict[str, Any]:
    # v4: Include FCF quality in financial health subscore
    financial_health = average([piotroski.get("score_pct"), altman.get("score_pct"), fcf_quality])
    graham_score = graham.get("score_pct")
    lynch_score = lynch.get("score_pct")

    # v3: Audit fix 1 — Lynch N/A caused 45% of errors.  When Lynch is
    # inapplicable the valuation subscore used Graham alone, which often
    # gave a mid-range score (50-83%) that inflated the composite above 62.
    # Penalty: if Lynch is N/A, discount the valuation subscore by 10% to
    # reflect the reduced coverage (one indicator instead of two).
    lynch_na = not lynch.get("applicable", False)
    valuation = average([graham_score, lynch_score])
    if valuation is not None and lynch_na:
        valuation = valuation * 0.90

    quality = greenblatt.get("score_pct")
    # v4: Include EPS momentum in growth subscore
    growth = average([growth_profile.get("score_pct"), eps_momentum])

    # v4: rebalanced — growth 20→30% (now includes EPS momentum),
    # financial_health 25→20% (now includes FCF quality),
    # valuation 30→25%, quality 25→25% unchanged.
    weighted_values = []
    if financial_health is not None:
        weighted_values.append((financial_health, 0.20))
    if valuation is not None:
        weighted_values.append((valuation, 0.25))
    if quality is not None:
        weighted_values.append((quality, 0.25))
    if growth is not None:
        weighted_values.append((growth, 0.30))

    if not weighted_values:
        return {
            "available": False,
            "warning": "Experimental score could not be computed because the required subscores were unavailable.",
        }

    total_weight = sum(weight for _, weight in weighted_values)
    weighted_score = sum(value * weight for value, weight in weighted_values) / total_weight

    # v3: Audit fix 3 — "Healthy but overvalued" caused 15% of FP errors.
    # When financial_health >> valuation by ≥30pt, the health score pulls
    # the composite into bullish territory even though valuation says it's
    # expensive.  Penalise the composite by the gap fraction scaled to
    # max -6pt so that borderline-bullish cases get pushed to neutral.
    if financial_health is not None and valuation is not None:
        health_val_gap = financial_health - valuation
        if health_val_gap >= 30:
            penalty = min((health_val_gap - 30) * 0.15 + 2.0, 6.0)
            weighted_score -= penalty

    # v3: Audit fix 4 — Graham too strict caused 8% of FN errors.
    # When Graham scores <30 but Piotroski is >60, the stock is
    # operationally healthy but fails Graham's strict value criteria
    # (dividend streak, low P/E, etc.).  Lift the floor of the composite
    # so that operationally sound companies aren't pushed into bearish.
    pio_score = piotroski.get("score_pct")
    if graham_score is not None and pio_score is not None:
        if graham_score < 30 and pio_score > 60:
            floor = 42.0  # just above the 40 bearish threshold
            if weighted_score < floor:
                weighted_score = floor

    if weighted_score >= 85:
        band = "strong"
    elif weighted_score >= 70:
        band = "good"
    elif weighted_score >= 62:
        band = "mixed_positive"
    elif weighted_score >= 40:
        band = "mixed"
    else:
        band = "weak"

    # v3: Audit fix 5 — Borderline calls (score 62-66) caused 5.5% of FP
    # errors.  Require ≥75% framework coverage for borderline bullish calls;
    # below that, too many indicators are missing to trust a marginal call.
    if band == "mixed_positive" and total_weight < 0.75:
        band = "mixed"

    if total_weight >= 0.9:
        confidence = "high"
    elif total_weight >= 0.65:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "available": True,
        "score": round(weighted_score, 1),
        "band": band,
        "confidence": confidence,
        "subscores": {
            "financial_health": round(financial_health, 1) if financial_health is not None else None,
            "valuation": round(valuation, 1) if valuation is not None else None,
            "quality": round(quality, 1) if quality is not None else None,
            "growth": round(growth, 1) if growth is not None else None,
            "eps_momentum": round(eps_momentum, 1) if eps_momentum is not None else None,
            "fcf_quality": round(fcf_quality, 1) if fcf_quality is not None else None,
        },
        "warning": "Experimental score is intended for backtesting and ranking experiments, not as a proven production trading signal.",
    }
