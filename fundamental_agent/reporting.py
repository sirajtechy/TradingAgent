from typing import Any, Dict, List


def build_text_report(result: Dict[str, Any]) -> str:
    company = result["company"]
    frameworks = result["frameworks"]
    lines: List[str] = []

    lines.append(f"{company['company_name']} ({company['ticker']})")
    lines.append(f"As of date: {result['request']['as_of_date']}")
    lines.append(f"Sector / Industry: {company['sector']} / {company['industry']}")
    lines.append(f"Price used: {result['as_of_price']['price']} on {result['as_of_price']['price_date']}")
    lines.append("")

    experimental = result.get("experimental_score")
    if experimental and experimental.get("available"):
        lines.append(
            f"Experimental score: {experimental['score']}/100 | Band: {experimental['band']} | Confidence: {experimental['confidence']}"
        )
        lines.append(experimental["warning"])
        lines.append("")

    piotroski = frameworks["piotroski"]
    lines.append(
        f"Piotroski: {piotroski.get('score')} / {piotroski.get('max_score')} | {piotroski.get('score_pct')}%"
    )

    altman = frameworks["altman"]
    if altman.get("applicable"):
        lines.append(
            f"Altman: Z {altman.get('z_score')} | Zone: {altman.get('zone')} | {altman.get('score_pct')}%"
        )
    else:
        lines.append("Altman: not applicable")

    graham = frameworks["graham"]
    lines.append(
        f"Graham: {graham.get('passes')} passes out of {graham.get('applicable_rules')} applicable rules | {graham.get('score_pct')}%"
    )

    greenblatt = frameworks["greenblatt"]
    if greenblatt.get("applicable"):
        lines.append(
            f"Greenblatt: EY {greenblatt.get('earnings_yield_pct')}% | ROC {greenblatt.get('return_on_capital_pct')}% | {greenblatt.get('score_pct')}%"
        )
    else:
        lines.append("Greenblatt: not applicable")

    lynch = frameworks["lynch"]
    if lynch.get("applicable"):
        cagr_years = lynch.get("cagr_lookback_years", 5)
        cagr_val = lynch.get(f"trailing_eps_cagr_{cagr_years}y_pct")
        lines.append(
            f"Lynch: Fair value ratio {lynch.get('fair_value_ratio')} | EPS CAGR ({cagr_years}y) {cagr_val}% | P/E {lynch.get('pe_ratio')} | {lynch.get('score_pct')}%"
        )
    else:
        lines.append("Lynch: not applicable")

    growth = frameworks["growth_profile"]
    if growth.get("applicable"):
        lines.append(
            f"Growth: Revenue YoY {growth.get('revenue_growth_yoy_pct')}% | EPS YoY {growth.get('eps_growth_yoy_pct')}% | {growth.get('score_pct')}%"
        )
    else:
        lines.append("Growth: not applicable")

    shariah = frameworks["shariah"]
    if shariah.get("applicable"):
        lines.append(
            f"Shariah ({shariah.get('standard')}): {shariah.get('status')} | Debt {shariah.get('debt_ratio')} | Cash {shariah.get('cash_ratio')} | Proxy impure revenue {shariah.get('impure_revenue_proxy_ratio')}"
        )

    warnings = result.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines)
