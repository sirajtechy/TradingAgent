# Fundamental Agent — Scoring Rules

> Actual scoring rules from `agents/fundamental/rules.py`.

---

## Architecture

- 6 evaluators, each produces a `score_pct` (0–100)
- 4 weighted subscores: financial_health, valuation, quality, growth
- Weighted composite → band → signal
- Plus standalone Shariah screening (pass/fail, not scored)

---

## Evaluator 1: Piotroski F-Score

9 binary (true/false) criteria. Score = passes / applicable × 100.

| # | Criterion | Pass When |
|---|---|---|
| F1 | ROA positive | `netIncome / totalAssets > 0` |
| F2 | Operating cash flow positive | `operatingCashFlow > 0` |
| F3 | ROA improving | `ROA_current > ROA_prior` |
| F4 | Quality of earnings | `operatingCashFlow > netIncome` |
| F5 | Leverage decreasing | `longTermDebt/totalAssets` fell YoY |
| F6 | Liquidity improving | `currentRatio` rose YoY |
| F7 | No dilution | `sharesOutstanding_current ≤ prior` |
| F8 | Gross margin improving | `grossMargin` rose YoY |
| F9 | Asset turnover improving | `revenue/totalAssets` rose YoY |

If a criterion's data is unavailable, it's skipped (not counted as fail).

---

## Evaluator 2: Altman Z-Score

Formula: `Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + X5`

| Component | Formula |
|---|---|
| X1 | Working Capital / Total Assets |
| X2 | Retained Earnings / Total Assets |
| X3 | EBIT / Total Assets |
| X4 | Market Cap / Total Liabilities |
| X5 | Revenue / Total Assets |

**Zone mapping:**
- Z ≤ 1.8 → distress → score_pct = 10
- Z 1.8–3.0 → grey → score_pct = 30 + ((Z − 1.8) / 1.2) × 25 → range 30–55
- Z 3.0–6.0 → safe → score_pct = 55 + ((Z − 3.0) / 3.0) × 15 → range 55–70
- Z > 6.0 → safe → score_pct = 70 (capped — Z=3 and Z=15 are both "safe")

Excluded: financials sector (Altman not designed for banks).

---

## Evaluator 3: Graham Defensive Investor

7 criteria, each pass/fail:

| # | Criterion | Pass When |
|---|---|---|
| G1 | Size | Revenue ≥ $500M |
| G2a | Current ratio | ≥ 2.0 |
| G2b | LT debt coverage | Long-term debt ≤ net current assets |
| G3 | Earnings stability | EPS > 0 for all 10 years |
| G4 | Dividend record | ≥ 20 consecutive years of dividends |
| G5 | EPS growth | Avg recent 3yr EPS ≥ 33% above avg oldest 3yr EPS (10yr window) |
| G6 | P/E ratio | Avg-3yr P/E ≤ 15 |
| G7 | P/B or combined | P/B ≤ 1.5, OR (P/E × P/B) ≤ 22.5 |

Score = passes / applicable × 100.

---

## Evaluator 4: Greenblatt Magic Formula

Two metrics, each bucket-scored, then averaged:

**Earnings Yield** = EBIT / Enterprise Value × 100

| EY % | Score |
|---|---|
| < 3% | 15 |
| 3–6% | 35 |
| 6–10% | 55 |
| 10–15% | 75 |
| > 15% | 100 |

**Return on Invested Capital** = EBIT / (PPE_net + Working Capital) × 100

| ROIC % | Score |
|---|---|
| < 5% | 15 |
| 5–12% | 35 |
| 12–25% | 55 |
| 25–40% | 75 |
| > 40% | 100 |

`score_pct = average(EY_score, ROIC_score)`

v3 fix: Thresholds raised from (3/5/8/12% and 5/10/15/25%) — old buckets scored most healthy companies ≥ 60, causing 81% of Greenblatt FPs.

Excluded: financials and utilities sectors.

---

## Evaluator 5: Peter Lynch Fair Value

1. **EPS CAGR** = `(current_EPS / historical_EPS)^(1/years) − 1` × 100
   - Lookback: min(available_years − 1, 5) → up to 5-year CAGR
2. **Fair Value Ratio** = `(EPS_CAGR% + dividend_yield%) / PE_ratio`

| Fair Value Ratio | Score |
|---|---|
| < 0.5 | 20 (overvalued) |
| 0.5–1.0 | 40 |
| 1.0–1.5 | 60 |
| 1.5–2.0 | 80 |
| > 2.0 | 100 (undervalued) |

Not applicable when: EPS ≤ 0, or < 2 years of statements.

---

## Evaluator 6: Growth Profile

Three components averaged:

**Revenue Growth YoY:**

| Growth % | Score |
|---|---|
| < 0% | 20 (shrinking) |
| 0–5% | 40 |
| 5–15% | 60 |
| 15–25% | 80 |
| > 25% | 100 |

**EPS Growth YoY:**

| Growth % | Score |
|---|---|
| < 0% | 20 |
| 0–10% | 40 |
| 10–20% | 60 |
| 20–30% | 80 |
| > 30% | 100 |

**Graham Growth Bonus:**
- If Graham G5 (10yr EPS growth ≥ 33%) passes → 100
- Otherwise → 20

`score_pct = average(revenue_score, eps_score, graham_bonus)`

---

## Shariah Screening (standalone, not scored)

Standard: AAOIFI (default). Denominator: market_cap or total_assets.

| Screen | Pass When |
|---|---|
| Business activity | No prohibited keywords (alcohol, gambling, tobacco, etc.) |
| Debt ratio | `totalDebt / denominator < threshold` (AAOIFI: 30%) |
| Cash ratio | `(cash + shortTermInvestments) / denominator < threshold` (AAOIFI: 30%) |
| Impure revenue | `interestIncome / revenue < 5%` |

Status: `pass`, `borderline_pass` (within 90% of threshold), `partial` (missing data), `fail`.

---

## Composite Scoring (experimental_score)

### Subscores & Weights

| Subscore | Composed From | Weight |
|---|---|---|
| financial_health | average(Piotroski, Altman) | 0.25 |
| valuation | average(Graham, Lynch) | 0.30 |
| quality | Greenblatt | 0.25 |
| growth | Growth Profile | 0.20 |

`composite = Σ(subscore × weight) / Σ(weights of available subscores)`

### v3 Fixes Applied to Composite

**Fix 1 — Lynch N/A discount:**
When Lynch is inapplicable (EPS ≤ 0, etc.), valuation subscore uses Graham alone. Discount: `valuation × 0.90` to reflect reduced coverage.

**Fix 2 — Greenblatt tighter buckets:**
See Evaluator 4 above — EY and ROIC thresholds raised.

**Fix 3 — Health-vs-valuation penalty:**
When `financial_health − valuation ≥ 30`:
`penalty = min((gap − 30) × 0.15 + 2.0, 6.0)`
Subtracts up to 6 points from composite. Prevents healthy-but-overvalued stocks from scoring bullish.

**Fix 4 — Graham floor:**
When `Graham score_pct < 30` AND `Piotroski score_pct > 60`:
Composite floor = 42 (above 40 bearish threshold). Prevents operationally sound companies from going bearish just because they fail strict Graham value criteria.

**Fix 5 — Borderline confidence gate:**
When `band = "mixed_positive"` AND `total_weight < 0.75` (less than 75% framework coverage):
Downgrade band to "mixed" (neutral). Too many missing indicators to trust a marginal bullish call.

### Band Mapping

| Score | Band | Signal |
|---|---|---|
| ≥ 85 | strong | bullish |
| 70–84 | good | bullish |
| 62–69 | mixed_positive | bullish (weakest) |
| 40–61 | mixed | neutral |
| < 40 | weak | bearish |

### Confidence

| Coverage Weight | Confidence |
|---|---|
| ≥ 0.90 | high |
| 0.65–0.89 | medium |
| < 0.65 | low |

---

## Data Quality

`coverage_ratio = applicable_frameworks / total_frameworks`

| Coverage | Warnings | Quality |
|---|---|---|
| ≥ 85% + ≤ 2 warnings | — | high |
| ≥ 60% | — | medium |
| < 60% | — | low |

---

## Output Key

Score stored under `experimental_score` key. The orchestrator reads this field.

---

*Updated: 2026-04-04 — Extracted from agents/fundamental/rules.py*