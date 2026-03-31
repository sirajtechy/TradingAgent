from datetime import date

from fundamental_agent.models import (
    AnalysisRequest,
    DividendEvent,
    PricePoint,
    Profile,
    RawFundamentalSnapshot,
    StatementEntry,
)


def make_snapshot() -> RawFundamentalSnapshot:
    request = AnalysisRequest(
        ticker="AAPL",
        as_of_date=date(2026, 3, 28),
        shariah_standard="aaoifi",
        include_experimental_score=True,
    )
    profile = Profile(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        description="Fixture data for deterministic tests.",
    )
    price_point = PricePoint(price_date=date(2026, 3, 27), price=186.5, volume=1000000)

    income_statements = [
        _income_statement(date(2024, 9, 28), date(2024, 11, 1), 2024, 391_035_000_000, 180_683_000_000, 93_736_000_000, 123_216_000_000, 6.08, 15_408_095_000, 4_250_000_000),
        _income_statement(date(2023, 9, 30), date(2023, 11, 3), 2023, 383_285_000_000, 169_148_000_000, 96_995_000_000, 120_427_000_000, 6.11, 15_520_000_000, 4_010_000_000),
        _income_statement(date(2022, 9, 24), date(2022, 10, 28), 2022, 394_328_000_000, 170_782_000_000, 99_803_000_000, 119_437_000_000, 6.11, 15_600_000_000, 2_825_000_000),
        _income_statement(date(2021, 9, 25), date(2021, 10, 29), 2021, 365_817_000_000, 152_836_000_000, 94_680_000_000, 108_949_000_000, 5.61, 16_865_000_000, 2_843_000_000),
        _income_statement(date(2020, 9, 26), date(2020, 10, 30), 2020, 274_515_000_000, 104_956_000_000, 57_411_000_000, 66_288_000_000, 3.31, 17_352_119_000, 3_763_000_000),
        _income_statement(date(2019, 9, 28), date(2019, 10, 31), 2019, 260_174_000_000, 98_392_000_000, 55_256_000_000, 63_930_000_000, 2.97, 18_595_652_000, 5_686_000_000),
        _income_statement(date(2018, 9, 29), date(2018, 11, 5), 2018, 265_595_000_000, 101_839_000_000, 59_531_000_000, 70_898_000_000, 3.00, 19_821_508_000, 2_745_000_000),
        _income_statement(date(2017, 9, 30), date(2017, 11, 3), 2017, 229_234_000_000, 88_186_000_000, 48_351_000_000, 61_344_000_000, 2.30, 21_006_772_000, 2_140_000_000),
        _income_statement(date(2016, 9, 24), date(2016, 10, 28), 2016, 215_639_000_000, 84_263_000_000, 45_687_000_000, 60_024_000_000, 2.08, 22_001_124_000, 1_348_000_000),
        _income_statement(date(2015, 9, 26), date(2015, 10, 28), 2015, 233_715_000_000, 93_626_000_000, 53_394_000_000, 71_230_000_000, 2.31, 23_022_000_000, 1_960_000_000),
    ]

    balance_statements = [
        _balance_statement(date(2024, 9, 28), date(2024, 11, 1), 2024, 364_980_000_000, 152_987_000_000, 176_392_000_000, 85_750_000_000, 106_629_000_000, 308_030_000_000, 56_950_000_000, 48_799_000_000, 29_943_000_000, 35_228_000_000, 45_680_000_000),
        _balance_statement(date(2023, 9, 30), date(2023, 11, 3), 2023, 352_583_000_000, 143_566_000_000, 145_308_000_000, 95_281_000_000, 111_088_000_000, 290_437_000_000, 62_146_000_000, 41_530_000_000, 29_965_000_000, 31_590_000_000, 43_715_000_000),
    ]

    cashflow_statements = [
        _cashflow_statement(date(2024, 9, 28), date(2024, 11, 1), 2024, 118_254_000_000),
        _cashflow_statement(date(2023, 9, 30), date(2023, 11, 3), 2023, 110_543_000_000),
    ]

    dividend_events = [
        DividendEvent(event_date=date(year, 6, 15), dividend=1.0, adjusted_dividend=1.0, frequency="annual")
        for year in range(2025, 2005, -1)
    ]

    return RawFundamentalSnapshot(
        request=request,
        profile=profile,
        price_point=price_point,
        income_statements=income_statements,
        balance_statements=balance_statements,
        cashflow_statements=cashflow_statements,
        dividend_events=dividend_events,
        warnings=[],
    )


def _income_statement(
    report_date,
    filing_date,
    fiscal_year,
    revenue,
    gross_profit,
    net_income,
    ebit,
    eps_diluted,
    weighted_average_shares,
    interest_income,
):
    return StatementEntry(
        report_date=report_date,
        filing_date=filing_date,
        fiscal_year=str(fiscal_year),
        period="FY",
        values={
            "revenue": revenue,
            "grossProfit": gross_profit,
            "netIncome": net_income,
            "ebit": ebit,
            "epsDiluted": eps_diluted,
            "weightedAverageShsOutDil": weighted_average_shares,
            "interestIncome": interest_income,
        },
    )


def _balance_statement(
    report_date,
    filing_date,
    fiscal_year,
    total_assets,
    total_current_assets,
    total_current_liabilities,
    long_term_debt,
    total_debt,
    total_liabilities,
    total_stockholders_equity,
    retained_earnings,
    cash_and_cash_equivalents,
    short_term_investments,
    property_plant_equipment_net,
):
    return StatementEntry(
        report_date=report_date,
        filing_date=filing_date,
        fiscal_year=str(fiscal_year),
        period="FY",
        values={
            "totalAssets": total_assets,
            "totalCurrentAssets": total_current_assets,
            "totalCurrentLiabilities": total_current_liabilities,
            "longTermDebt": long_term_debt,
            "totalDebt": total_debt,
            "totalLiabilities": total_liabilities,
            "totalStockholdersEquity": total_stockholders_equity,
            "retainedEarnings": retained_earnings,
            "cashAndCashEquivalents": cash_and_cash_equivalents,
            "shortTermInvestments": short_term_investments,
            "propertyPlantEquipmentNet": property_plant_equipment_net,
        },
    )


def _cashflow_statement(report_date, filing_date, fiscal_year, operating_cash_flow):
    return StatementEntry(
        report_date=report_date,
        filing_date=filing_date,
        fiscal_year=str(fiscal_year),
        period="FY",
        values={
            "operatingCashFlow": operating_cash_flow,
        },
    )
