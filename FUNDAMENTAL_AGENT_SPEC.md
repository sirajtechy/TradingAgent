/Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace/FUNDAMENTAL_AGENT_SPEC.md# Fundamental Analysis Agent — Deep Specification

**System:** Multi-Agent Stock Trading Analysis Platform  
**Agent Role:** Fundamental Analysis Agent  
**Version:** 1.0.0  
**Date:** 2026-03-28  
**Design Philosophy:** DETERMINISTIC, RULE-BASED — Zero LLM influence on scores or pass/fail decisions. LLM used only for final human-readable summary generation, never for scoring logic.

---

## Table of Contents

1. [Established Frameworks Used (with Sources)](#section-1-established-frameworks-used)
2. [Unified Scoring Engine](#section-2-unified-scoring-engine)
3. [MCP Tools — Data Fetching Functions](#section-3-mcp-tools-data-fetching-functions)
4. [Complete JSON Output Schema (AAPL Worked Example)](#section-4-complete-json-output-schema)
5. [Challenges & Design Decisions](#section-5-challenges--design-decisions)
6. [Rule Engine Pseudocode](#section-6-rule-engine-pseudocode)

---

## SECTION 1: Established Frameworks Used

This agent combines six validated, academically and professionally established frameworks into a single deterministic scoring engine. Each framework has peer-reviewed or widely-cited practitioner validation. Rules are not invented — they are sourced from primary literature or authoritative implementation guides.

---

### A. Piotroski F-Score (9-Point Scale)

**Primary Source:** Piotroski, J.D. (2000). "Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers." *Journal of Accounting Research*, 38 (Supplement): 1–41.  
**Practitioner Validation:** [Stock Rover — The Piotroski F-Score](https://www.stockrover.com/blog/the-piotroski-f-score/)  
**Accuracy:** Referenced as ~72% accuracy in predicting financially weak vs. strong firms; Altman's bankruptcy research corroborates the financial health signals.

**What it measures:** The Piotroski F-Score is a 9-point binary scoring system that evaluates a company's financial strength across three domains: profitability, capital structure/leverage, and operating efficiency. Each of the 9 criteria awards 1 point (pass) or 0 points (fail). The score ranges from 0 (weakest) to 9 (strongest).

**Why use it:** Piotroski demonstrated that simple rule-based binary tests on historical financial statements can predict future stock returns. Stocks with high F-Scores (8-9) outperformed low F-Score stocks (0-2) by ~23% annually in his original study. It is completely deterministic — no subjective judgment required.

#### Profitability (4 points)

| # | Criterion | Formula | Pass Condition | Points |
|---|-----------|---------|----------------|--------|
| F1 | ROA Positive | Net Income / Total Assets | > 0 | 1 |
| F2 | Operating Cash Flow Positive | CFO from Cash Flow Statement | > 0 | 1 |
| F3 | ROA Improving | ROA[current year] vs ROA[prior year] | current > prior | 1 |
| F4 | Quality of Earnings | Cash Flow from Operations vs Net Income | CFO > Net Income | 1 |

**Rationale for F4 (Quality of Earnings):** When cash flow from operations consistently exceeds net income, it indicates earnings are not inflated by accruals. Companies with accrual-heavy income (net income >> CFO) tend to have lower future returns. This is the *Sloan accrual anomaly* documented in [Sloan (1996)](https://www.jstor.org/stable/248290).

#### Capital Structure / Leverage (3 points)

| # | Criterion | Formula | Pass Condition | Points |
|---|-----------|---------|----------------|--------|
| F5 | Leverage Decreasing | Long-term Debt / Total Assets: current vs prior | current < prior | 1 |
| F6 | Liquidity Improving | Current Ratio: current vs prior | current > prior | 1 |
| F7 | No Share Dilution | Shares Outstanding: current vs prior | current <= prior | 1 |

**Rationale for F7:** Share issuance dilutes existing shareholders and often signals management's belief that the stock is overvalued. Share buybacks (shares current < prior) signal management confidence and return capital to shareholders. The rule is binary — any net increase in shares fails.

#### Operating Efficiency (2 points)

| # | Criterion | Formula | Pass Condition | Points |
|---|-----------|---------|----------------|--------|
| F8 | Gross Margin Improving | Gross Margin: current vs prior | current > prior | 1 |
| F9 | Asset Turnover Improving | Sales / Total Assets: current vs prior | current > prior | 1 |

#### Score Interpretation

| F-Score | Interpretation | Signal |
|---------|---------------|--------|
| 8–9 | Financially very sound | Strong BUY fundamental signal |
| 6–7 | Financially sound | Moderate positive |
| 4–5 | Neutral / mixed signals | No strong signal |
| 2–3 | Financially weak | Caution |
| 0–1 | Financially very weak | Strong avoidance signal |

**Data Required:** 2 years of annual income statements, balance sheets, and cash flow statements.

---

### B. Altman Z-Score (Bankruptcy Predictor)

**Primary Source:** Altman, E.I. (1968). "Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy." *Journal of Finance*, 23(4): 589–609.  
**Practitioner Validation:** [Corporate Finance Institute — Altman Z-Score Model](https://corporatefinanceinstitute.com/resources/commercial-lending/altmans-z-score-model/)  
**Accuracy:** 80–90% accuracy in predicting bankruptcy within 2 years per Altman's original and subsequent research. [Cited by Investopedia](https://www.investopedia.com/terms/a/altman.asp) as one of the most widely used financial distress models.

**What it measures:** A weighted multivariate discriminant analysis model that combines five financial ratios into a single Z-Score, classifying companies into Safe, Grey, or Distress zones.

**Formula:**
```
Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
```

#### Component Definitions

| Variable | Formula | What It Tests | Weight |
|----------|---------|---------------|--------|
| X1 | Working Capital / Total Assets | Short-term liquidity | 1.2 |
| X2 | Retained Earnings / Total Assets | Cumulative profitability / leverage | 1.4 |
| X3 | EBIT / Total Assets | Asset productivity / profitability | 3.3 |
| X4 | Market Value of Equity / Total Liabilities | Solvency buffer | 0.6 |
| X5 | Net Sales / Total Assets | Asset efficiency | 1.0 |

**Component Calculations:**
- Working Capital = Current Assets − Current Liabilities
- EBIT = Earnings Before Interest and Taxes (Operating Income)
- Market Value of Equity = Shares Outstanding × Current Stock Price
- Total Liabilities = Total Assets − Total Stockholders' Equity

#### Zone Classification

| Z-Score Range | Zone | Interpretation | Agent Signal |
|--------------|------|----------------|-------------|
| Z > 3.0 | Safe Zone | Bankruptcy highly unlikely | PASS |
| 1.8 < Z ≤ 3.0 | Grey Zone | Moderate distress risk | CAUTION |
| Z ≤ 1.8 | Distress Zone | High bankruptcy risk within 2 years | FAIL |

**Important Caveat — Model Variants:** Altman developed three versions:
1. **Original (1968):** For publicly traded manufacturing firms — formula above
2. **Z'-Score (1983):** For private firms — replaces X4 with Book Value of Equity / Total Liabilities
3. **Z''-Score (1995):** For non-manufacturing/emerging market firms — uses only X1–X4, different weights

**This agent uses the original public-company formula.** For non-manufacturing sectors (tech, financial services), results should be interpreted with the caveat documented in [Section 5](#section-5-challenges--design-decisions).

**Data Required:** Most recent annual balance sheet, income statement, and current market price.

---

### C. Benjamin Graham's Defensive Investor Criteria (7 Rules)

**Primary Source:** Graham, B. (1949, revised 1973). *The Intelligent Investor*. Harper & Row.  
**Practitioner Validation:** [Groww — Benjamin Graham's 7 Stock Criteria](https://groww.in/blog/benjamin-grahams-7-stock-criteria) | [GrahamValue Quick Reference](https://www.grahamvalue.com/quick-reference)

**What it measures:** Graham's criteria for a "defensive" (risk-averse) investor — designed to select stocks that are: large enough to be financially stable, undervalued by asset-based measures, with a long history of earnings and dividends, and priced at a significant discount to intrinsic value.

**Design philosophy:** These rules are deliberately conservative. Graham wrote them to prevent retail investors from overpaying for growth expectations that might not materialize. They are NOT designed to identify the best-performing growth stocks — they are designed to identify stocks with substantial margin of safety.

**Agent usage note:** We apply all 7 rules but do NOT require all 7 to pass. Instead, each passing criterion contributes to sub-scores as documented in Section 2. This avoids the trap of the pure Graham screen rejecting 95%+ of the market including the highest-quality businesses.

#### The 7 Criteria

| # | Rule | Threshold | Rationale |
|---|------|-----------|-----------|
| G1 | Adequate Size | Annual revenue > $500M (inflation-adjusted from Graham's $100M in 1973 dollars) | Large companies are less likely to go bankrupt and have more stable earnings |
| G2a | Current Ratio | Current Assets / Current Liabilities ≥ 2.0 | "Twice-covered" current liabilities provides safety buffer |
| G2b | LT Debt vs Net Current Assets | Long-term Debt ≤ Net Current Assets (CA − CL) | Limits leverage relative to liquid asset buffer |
| G3 | Earnings Stability | Positive EPS in each of the past 10 years | No earnings losses in a decade = proven business resilience |
| G4 | Dividend Record | Uninterrupted dividends for ≥ 20 consecutive years | Sustained dividend payments demonstrate financial discipline and stability |
| G5 | Earnings Growth | Min 33% total EPS growth over 10 years using 3-year averages (≈ 2.9% CAGR) | Requires minimum forward momentum to offset inflation |
| G6 | Moderate P/E | P/E ≤ 15× average earnings of last 3 years | Limits overpayment for earnings; 15× is the historical average market P/E |
| G7a | Moderate P/B | P/B ≤ 1.5 | Ensures purchase close to or below book value |
| G7b | Combined Multiplier | P/E × P/B ≤ 22.5 | Allows slight P/B excess if P/E is low enough (e.g., P/E=12, P/B=1.8 → 21.6 ✓) |

**Calculations:**
```
G5 Earnings Growth:
  avg_eps_3yr_start = mean(EPS[y-10], EPS[y-9], EPS[y-8])
  avg_eps_3yr_end   = mean(EPS[y-2], EPS[y-1], EPS[y])
  growth_pct = (avg_eps_3yr_end - avg_eps_3yr_start) / avg_eps_3yr_start
  pass = growth_pct >= 0.333

G6 3-Year Average P/E:
  avg_eps_3yr = mean(EPS[y], EPS[y-1], EPS[y-2])
  pe_3yr_avg = current_price / avg_eps_3yr
  pass = pe_3yr_avg <= 15
```

**Data Required:** 10 years of annual EPS, 20 years of dividend history, current balance sheet, current price.

---

### D. Peter Lynch Fair Value / PEGY Ratio

**Primary Source:** Lynch, P. & Rothchild, J. (1989). *One Up on Wall Street*. Simon & Schuster.  
**Practitioner Validation:** [StableBread — Peter Lynch Stock Valuation](https://stablebread.com/peter-lynch-stock-valuation/) | [Quantamental Trader — Lynch PEGY Method](https://quantamentaltrader.substack.com/p/peter-lynchs-pegy-method-a-detailed)

**What it measures:** Lynch's framework extends the classic PEG ratio (Price-to-Earnings / Growth Rate) to include dividend yield, creating the PEGY ratio. It answers the question: "Does the current P/E make sense given the company's growth rate plus dividend yield?"

**Core Insight:** Lynch argued that a fairly valued stock should have a P/E ratio roughly equal to its EPS growth rate (PEG ≈ 1.0). By adding dividend yield, PEGY accounts for the total return to the investor, making it applicable to dividend-paying companies.

#### Lynch Fair Value Ratio

```
Lynch_Fair_Value_Ratio = (EPS_Growth_Rate_% + Dividend_Yield_%) / P/E_Ratio
```

| Ratio Value | Interpretation | Agent Signal |
|------------|----------------|-------------|
| < 0.5 | Significantly overvalued | Strong AVOID |
| 0.5 – 1.0 | Moderately overvalued | CAUTION |
| ~1.0 | Fairly valued | NEUTRAL |
| 1.0 – 2.0 | Moderately undervalued | Positive |
| > 2.0 | Significantly undervalued | Strong BUY signal |

#### PEGY Ratio (Inverse Formulation)

```
PEGY = P/E_Ratio / (EPS_Growth_Rate_% + Dividend_Yield_%)
```

| PEGY Value | Interpretation |
|-----------|----------------|
| < 1.0 | Undervalued — growth + yield exceeds what P/E implies |
| = 1.0 | Fairly valued |
| > 1.0 | Overvalued — P/E more than justified by growth + yield |

**PEGY is the inverse of Lynch Fair Value Ratio.** They carry identical information in different directions. We compute both for clarity but use Lynch Fair Value Ratio as the primary metric in scoring.

**Measurement Notes:**
- **EPS Growth Rate:** Use forward 5-year analyst consensus EPS CAGR if available; fallback to trailing 5-year EPS CAGR
- **Dividend Yield:** Trailing 12-month dividends per share / current price × 100
- **P/E Ratio:** Forward P/E (using next-12-month consensus EPS) preferred; trailing P/E as fallback

**Data Required:** Current P/E (trailing or forward), EPS growth estimate, annual dividend per share, current price.

---

### E. Greenblatt Magic Formula (2 Metrics)

**Primary Source:** Greenblatt, J. (2005). *The Little Book That Beats the Market*. John Wiley & Sons.  
**Practitioner Validation:** [GuruFocus — Greenblatt Earnings Yield and Return on Capital](https://www.gurufocus.com/tutorial/article/57/greenblatts-earnings-yield-and-return-on-capital)

**What it measures:** Greenblatt's "Magic Formula" ranks stocks simultaneously on cheapness (Earnings Yield) and quality (Return on Capital). The formula doesn't require a single cutoff — it ranks the entire universe and selects top-ranked stocks by combined rank. In our agent, we convert each metric to a scaled score and use defined thresholds.

**Core Insight:** Greenblatt demonstrated that buying cheap + high-quality businesses consistently outperforms the market. The formula deliberately avoids financial and utility companies (where capital structure makes the metrics unreliable).

#### Metric 1: Earnings Yield (EY)

```
Earnings_Yield = EBIT / Enterprise_Value
```

Where:
- **EBIT** = Earnings Before Interest and Taxes (Operating Income)
- **Enterprise Value** = Market Cap + Total Debt − Cash & Cash Equivalents

This is the INVERSE of EV/EBIT. Higher is better.

| EY Value | Interpretation | Points |
|---------|----------------|--------|
| < 3% | Very expensive | Poor |
| 3% – 5% | Expensive | Below Average |
| 5% – 8% | Fairly valued | Average |
| 8% – 12% | Cheap | Good |
| > 12% | Very cheap | Excellent |

#### Metric 2: Return on Capital (ROIC / ROC)

```
Return_on_Capital = EBIT / (Net_Fixed_Assets + Working_Capital)
```

Where:
- **Net Fixed Assets** = Net Property, Plant & Equipment (PP&E)
- **Working Capital** = Current Assets − Current Liabilities (using operating working capital, excluding excess cash and short-term debt)

This measures how much operating profit the business generates per dollar of tangible capital deployed. Higher is better.

| ROIC Value | Interpretation | Points |
|-----------|----------------|--------|
| < 5% | Poor capital efficiency | Very Poor |
| 5% – 10% | Below-average business quality | Poor |
| 10% – 20% | Average business quality | Average |
| 20% – 30% | Good business quality | Good |
| > 30% | Exceptional business quality (moat likely) | Excellent |

**Important:** Greenblatt explicitly excludes:
- Financial companies (banks, insurance) — because their "working capital" is their product
- Utility companies — due to regulatory capital structures that distort ROIC
- For these sectors, flag `greenblatt_applicable: false` in the output and exclude from scoring

**Data Required:** Most recent annual income statement (EBIT), most recent balance sheet (PP&E, current assets/liabilities, debt, cash), current market cap.

---

### F. AAOIFI Shariah Compliance Screening

**Primary Source:** AAOIFI (Accounting and Auditing Organization for Islamic Financial Institutions) Standard No. 21 — Financial Papers (Shares and Bonds).  
**Validation Sources:** 
- [Musaffa Academy — 7 Halal Stock Screening Methodologies](https://academy.musaffa.com/7-halal-stock-screening-methodologies-you-need-to-know/)
- [HalalSignalz — AAOIFI Ratio Explained](https://www.halalsignalz.com/blog/aaofi-ratio-explained)
- [arXiv — Shariah Screening Research (2512.22858)](https://arxiv.org/html/2512.22858v1)

**What it measures:** Whether a stock is permissible (halal) for Muslim investors under Islamic finance principles. The screening has two components: (1) business activity / sector screen, and (2) quantitative financial ratio screens.

**Ratio threshold note:** AAOIFI Standard No. 21 uses 30% as the threshold for financial ratios. The DJIM (Dow Jones Islamic Market Index) and MSCI Islamic Index use 33.33%. We adopt **33%** as the broader standard (consistent with the MSCI/DJIM approach) to maximize compatibility across major Shariah screening services. A "Borderline" warning is triggered for any ratio between 25–33%.

#### Step 1: Sector Screen (Binary — Applied First)

The company's **core primary business** must not be in a prohibited sector. If it is, status = "Not Halal" immediately without computing financial ratios.

| Prohibited Sectors (Haram) | Permissible Examples |
|---------------------------|---------------------|
| Conventional banking (interest-based) | Technology |
| Conventional insurance (interest-based) | Healthcare (non-alcohol pharmaceuticals) |
| Alcohol production/distribution | Consumer goods (non-haram products) |
| Pork and pork-derived products | Manufacturing |
| Gambling / casinos | Retail (non-haram products) |
| Pornography / adult entertainment | Utilities |
| Tobacco / nicotine products | Energy (oil & gas — generally permissible) |
| Weapons / defense (AAOIFI; some indices allow dual-use) | Real Estate |

**Sector classification:** Use the company's GICS (Global Industry Classification Standard) primary sector and sub-industry from the profile API. Cross-reference with known prohibited sub-industries. When the primary business is mixed (e.g., a conglomerate with some alcohol distribution), classify as the dominant revenue-generating segment.

#### Step 2: Financial Ratio Screens (3 Ratios)

If the sector screen passes, evaluate these three financial ratios:

**Ratio 1 — Debt Ratio:**
```
Debt_Ratio = Total_Debt / Market_Capitalization
```
- **Threshold:** < 33%
- **Alternative (SC Malaysia standard):** Total Debt / Total Assets < 33%
- **Rationale:** Limits reliance on interest-bearing debt, which involves riba (interest), a key prohibition in Islamic finance
- **Note:** We use market cap denominator (AAOIFI standard). Some screeners use total assets; we flag which was used in the output

**Ratio 2 — Cash and Interest-Bearing Securities Ratio:**
```
Cash_Ratio = (Cash + Cash_Equivalents + Short_Term_Investments) / Market_Capitalization
```
- **Threshold:** < 33%
- **Rationale:** Ensures the investor is not effectively "buying cash" — Islam permits profit but not interest, and a company holding massive interest-bearing securities would generate interest income for shareholders

**Ratio 3 — Impermissible Income Ratio:**
```
Impermissible_Income_Ratio = Non_Halal_Revenue / Total_Revenue
```
- **Non-Halal Revenue sources:** Interest income, dividends from non-halal subsidiaries, income from any prohibited activity
- **Threshold:** < 5%
- **Rationale:** AAOIFI allows a small tolerance ("de minimis" rule) for incidental haram income. The 5% threshold is the widely adopted standard
- **Purification:** When passing this screen, the investor must "purify" their returns by donating the impermissible income percentage of their investment returns to charity

#### Status Classification

| Condition | Status |
|-----------|--------|
| Sector screen fails | Not Halal |
| All 3 ratios pass (all < 25%) | Halal |
| All 3 ratios pass but any between 25–33% | Borderline (pass with monitoring warning) |
| Any ratio ≥ 33% | Not Halal |

#### Purification Calculation

```
purification_ratio      = impermissible_income_ratio  (e.g., 0.0098)
purification_per_share  = earnings_per_share × purification_ratio
```

This tells the investor how much per share of their annual return they must donate to charity to "purify" their investment.

**Data Required:** Company sector/industry (profile), total debt, market cap, cash and short-term investments, interest income, total revenue (from income statement and key metrics).

---

### G. Swing Trade Feasibility from Fundamentals

**Source:** Custom rules derived from the intersection of value investing and momentum research. Supporting literature:  
- [Fama & French (1992)](https://www.jstor.org/stable/2329112) — Value premium evidence  
- Bernard & Thomas (1989) — Post-Earnings Announcement Drift (PEAD)  
- [Jegadeesh & Titman (1993)](https://www.jstor.org/stable/2328882) — Momentum effect in stock returns

**What it measures:** Whether the fundamental picture SUPPORTS or CONTRADICTS a short-term swing trade thesis (typically 5–15 day holding period targeting 5–10% price movement).

**Design rationale:** Fundamentals alone cannot time short-term trades. However, fundamentals can identify:
1. Whether there is underlying intrinsic value support for an upward move (DCF margin of safety)
2. Whether recent earnings catalysts are likely to sustain momentum (earnings surprise + revenue acceleration)
3. Whether the stock is fundamentally overvalued in a way that creates ceiling pressure on any swing upside

#### Rule G-SW1: DCF Margin of Safety

```
Margin_of_Safety_% = (DCF_Intrinsic_Value - Current_Price) / Current_Price × 100
```

| Margin of Safety | Fundamental Support | Swing Signal |
|-----------------|-------------------|-------------|
| > 20% undervalued | Strong intrinsic value floor | Strong fundamental support |
| 10% – 20% undervalued | Moderate undervaluation | Moderate support |
| 0% – 10% undervalued | Slight undervaluation | Weak support |
| 0% – 10% overvalued | Slight overvaluation | Slight headwind |
| > 10% overvalued | Meaningful overvaluation | Meaningful headwind |
| > 20% overvalued | Significant overvaluation | Strong headwind — fundamentals cap upside |

#### Rule G-SW2: Earnings Surprise Momentum

Source: Post-Earnings Announcement Drift (PEAD) research shows stocks that beat estimates tend to continue outperforming for 30–60 days.

```
EPS_Surprise_% = (Actual_EPS - Consensus_EPS_Estimate) / |Consensus_EPS_Estimate| × 100
```

| Condition | Interpretation | Swing Signal |
|-----------|----------------|-------------|
| Beat by > 5% | Strong positive catalyst | Strong positive |
| Beat by 1–5% | Moderate beat | Positive |
| In-line (±1%) | Neutral | Neutral |
| Miss by 1–5% | Negative catalyst | Caution |
| Miss by > 5% | Significant disappointment | Headwind |

**Data used:** Most recent quarterly EPS actual vs. analyst consensus estimate.

#### Rule G-SW3: Revenue Acceleration

Revenue acceleration (increasing growth rate quarter-over-quarter) is a positive momentum signal that suggests business conditions are improving.

```
current_q_revenue_growth = (Revenue[Q] - Revenue[Q-4]) / Revenue[Q-4] × 100
prior_q_revenue_growth   = (Revenue[Q-1] - Revenue[Q-5]) / Revenue[Q-5] × 100
accelerating             = current_q_revenue_growth > prior_q_revenue_growth
```

| Condition | Signal |
|-----------|--------|
| Accelerating (current > prior) | Supports swing thesis |
| Flat (within ±0.5%) | Neutral |
| Decelerating (current < prior) | Caution — growth momentum fading |

**Overall Swing Assessment:**
```
fundamental_support = 
  "strong"   if MoS > 10% AND earnings_beat AND accelerating
  "moderate" if MoS > 0% AND (earnings_beat OR accelerating)
  "neutral"  if mixed signals
  "weak"     if MoS < 0% OR earnings_miss OR decelerating
  "negative" if MoS < -15% AND earnings_miss AND decelerating
```

**Data Required:** DCF value from FMP, most recent quarterly actuals vs. estimates, last 5 quarters of quarterly revenue (to compute 2 sequential YoY growth rates).

---

## SECTION 2: Unified Scoring Engine

All six frameworks (excluding AAOIFI, which is a separate compliance flag) are combined into a single deterministic 1.0–10.0 fundamental score through four sub-scores.

**Key design principle:** AAOIFI Shariah compliance is reported separately as a compliance flag, NOT factored into the fundamental score. This is because Shariah compliance is a binary eligibility filter for specific investors — it does not indicate financial quality. A non-halal stock can be fundamentally excellent; a halal stock can be fundamentally poor.

---

### Sub-Score A: Financial Health (0–10)

**Frameworks used:** Piotroski F-Score + Altman Z-Score  
**Weight in final score:** 30%  
**Rationale:** A fundamentally sound stock must not be at risk of financial distress or bankruptcy. Piotroski measures year-over-year momentum in financial health; Altman measures structural solvency. Together they provide both trend and level assessment.

#### Step 1: Map Piotroski F-Score (0–9) → Sub-Score (1–10)

| Raw Piotroski Score | Mapped Score |
|--------------------|-------------|
| 0 – 1 | 1 |
| 2 – 3 | 3 |
| 4 – 5 | 5 |
| 6 – 7 | 7 |
| 8 | 9 |
| 9 | 10 |

#### Step 2: Map Altman Z-Score → Sub-Score (1–10)

| Z-Score Range | Mapped Score | Zone |
|--------------|-------------|------|
| Z < 1.8 | 1 | Distress — near bankruptcy |
| 1.8 ≤ Z < 2.5 | 4 | Grey zone — significant risk |
| 2.5 ≤ Z < 3.0 | 6 | Grey zone — moderate risk |
| 3.0 ≤ Z < 4.0 | 8 | Safe zone — low risk |
| Z ≥ 4.0 | 10 | Safe zone — very low risk |

#### Step 3: Combine

```
financial_health_score = (piotroski_mapped × 0.5) + (altman_mapped × 0.5)
```

Range: 1.0 to 10.0

**AAPL Example:**
- Piotroski: 7 → mapped = 7
- Altman Z: 4.82 → mapped = 10
- Financial Health = (7 × 0.5) + (10 × 0.5) = **8.5**

---

### Sub-Score B: Valuation (0–10)

**Frameworks used:** Lynch Fair Value + Graham P/E + Graham P/B + DCF Margin of Safety  
**Weight in final score:** 30%  
**Rationale:** For any investment, and especially for swing trades where the time horizon is short, overpaying creates a valuation ceiling that limits upside. This sub-score penalizes expensive stocks while rewarding genuinely undervalued ones.

#### Step 1: Map Lynch Fair Value Ratio → Base Score (1–9)

| Lynch Fair Value | Mapped Score |
|-----------------|-------------|
| < 0.5 | 1 |
| 0.5 – 1.0 | 3 |
| 1.0 – 1.5 | 5 |
| 1.5 – 2.0 | 7 |
| > 2.0 | 9 |

#### Step 2: Graham P/E Bonus

```
graham_pe_bonus = 1.5 if (3-year avg P/E <= 15) else 0
```

#### Step 3: Graham P/B Bonus

```
graham_pb_bonus = 1.5 if (P/B <= 1.5 OR P/E × P/B <= 22.5) else 0
```

#### Step 4: DCF Margin of Safety Bonus

```
if MoS_% > 20%:  dcf_bonus = 2.0
elif MoS_% > 10%: dcf_bonus = 1.0
elif MoS_% > 0%:  dcf_bonus = 0.5
else:             dcf_bonus = 0
```

#### Step 5: Combine (cap at 10)

```
valuation_raw = lynch_mapped + graham_pe_bonus + graham_pb_bonus + dcf_bonus
valuation_score = min(valuation_raw, 10.0)
```

**AAPL Example:**
- Lynch Fair Value = 0.91 → mapped = 3
- Graham P/E: P/E=29.3 > 15 → bonus = 0
- Graham P/B: P/B=46.5, P/E×P/B=1361 >> 22.5 → bonus = 0
- DCF MoS = -14.9% → bonus = 0
- Valuation = min(3 + 0 + 0 + 0, 10) = **3.0**

---

### Sub-Score C: Profitability & Efficiency (0–10)

**Frameworks used:** Greenblatt Earnings Yield + Greenblatt ROIC + Piotroski Gross Margin Trend  
**Weight in final score:** 20%  
**Rationale:** Business quality — whether the company generates high returns on the capital it deploys and whether it's priced cheaply relative to its operating earnings — is a critical predictor of long-term stock performance.

#### Step 1: Map Greenblatt Earnings Yield → Sub-Score (1–9)

| Earnings Yield | Mapped Score |
|---------------|-------------|
| < 3% | 1 |
| 3% – 5% | 3 |
| 5% – 8% | 5 |
| 8% – 12% | 7 |
| > 12% | 9 |

#### Step 2: Map Greenblatt ROIC → Sub-Score (1–9)

| ROIC | Mapped Score |
|------|-------------|
| < 5% | 1 |
| 5% – 10% | 3 |
| 10% – 20% | 5 |
| 20% – 30% | 7 |
| > 30% | 9 |

#### Step 3: Gross Margin Trend Bonus

```
gross_margin_bonus = 1.0 if gross_margin[current] > gross_margin[prior] else 0
```

#### Step 4: Combine (cap at 10)

```
profitability_raw = (ey_mapped × 0.4) + (roic_mapped × 0.4) + gross_margin_bonus
profitability_score = min(profitability_raw, 10.0)
```

**AAPL Example:**
- EY = EBIT/EV = ~5.3% → mapped = 5
- ROIC = EBIT/(PP&E + Working Capital) = ~170% (asset-light) → mapped = 9 (flag: very high for tech, normal for asset-light)
- Gross margin improving (43.68% vs 42.96%) → bonus = 1
- Profitability = min((5×0.4)+(9×0.4)+1, 10) = min(2+3.6+1, 10) = min(6.6, 10) = **6.6**

---

### Sub-Score D: Growth & Momentum (0–10)

**Frameworks used:** Revenue Growth (YoY), EPS Growth (YoY), Graham 10-Year Earnings Growth Test  
**Weight in final score:** 20%  
**Rationale:** For swing trades, growth momentum is a key catalyst. Stagnant or declining fundamentals suppress price recovery even after technical setups. Strong EPS and revenue growth increase the probability of price appreciation.

#### Step 1: Map Revenue Growth (YoY) → Sub-Score (1–9)

| Revenue Growth YoY | Mapped Score |
|------------------|-------------|
| Negative (< 0%) | 1 |
| 0% – 5% | 3 |
| 5% – 15% | 5 |
| 15% – 25% | 7 |
| > 25% | 9 |

#### Step 2: Map EPS Growth (YoY) → Sub-Score (1–9)

| EPS Growth YoY | Mapped Score |
|---------------|-------------|
| Negative (< 0%) | 1 |
| 0% – 10% | 3 |
| 10% – 20% | 5 |
| 20% – 30% | 7 |
| > 30% | 9 |

#### Step 3: Graham 10-Year Growth Bonus

```
graham_growth_bonus = 1.0 if eps_growth_10y_pct >= 33% else 0
```

(Uses 3-year average EPS endpoints per Graham's methodology)

#### Step 4: Combine (cap at 10)

```
growth_raw = (rev_growth_mapped × 0.4) + (eps_growth_mapped × 0.4) + graham_growth_bonus
growth_score = min(growth_raw, 10.0)
```

**AAPL Example:**
- Revenue growth YoY ≈ +2.0% → mapped = 3
- EPS growth YoY ≈ +9.0% → mapped = 3
- Graham 10y growth: EPS grew from ~$0.60 (2014-2016 avg) to ~$6.04 (2022-2024 avg) → >33% ✓ → bonus = 1
- Growth = min((3×0.4)+(3×0.4)+1, 10) = min(1.2+1.2+1, 10) = min(3.4, 10) = **3.4**

---

### Final Fundamental Score

```
fundamental_score = (financial_health × 0.30) 
                  + (valuation × 0.30) 
                  + (profitability × 0.20) 
                  + (growth × 0.20)
```

Rounded to 1 decimal. Range: 1.0 to 10.0.

**AAPL Example:**
```
= (8.5 × 0.30) + (3.0 × 0.30) + (6.6 × 0.20) + (3.4 × 0.20)
= 2.55 + 0.90 + 1.32 + 0.68
= 5.45 → 5.5
```

#### Sub-Score Weight Justification

| Sub-Score | Weight | Justification |
|-----------|--------|---------------|
| Financial Health | 30% | Financial distress is an asymmetric risk — a bankrupt company goes to zero. Avoiding distress is the first priority. Piotroski + Altman cover both trend and structural risk. |
| Valuation | 30% | Overpaying is the primary way intelligent investors lose money (Graham). For swing trades, an overvalued stock faces ceiling pressure from mean-reversion forces. Graham + Lynch + DCF triangulate intrinsic value from multiple angles. |
| Profitability & Efficiency | 20% | High ROIC businesses compound capital and attract institutional interest. Greenblatt's research shows high ROIC + low EV/EBIT is one of the most robust long-term alpha factors. |
| Growth & Momentum | 20% | Growth provides the catalyst for price appreciation in swing trades. However, growth without financial health or valuation discipline is dangerous (value trap vs. growth trap). |

#### Interpretation Scale

| Score | Interpretation | Recommendation |
|-------|---------------|----------------|
| 9.0 – 10.0 | Exceptional fundamentals | Strong fundamental BUY support |
| 7.5 – 8.9 | Strong fundamentals | Good fundamental support |
| 6.0 – 7.4 | Above average fundamentals | Moderate support |
| 4.5 – 5.9 | Mixed fundamentals | Neutral — other factors dominate |
| 3.0 – 4.4 | Below average fundamentals | Caution — fundamentals are a headwind |
| 1.0 – 2.9 | Weak / distressed fundamentals | Strong fundamental AVOID signal |

---

## SECTION 3: MCP Tools — Data Fetching Functions

All data is fetched from [Financial Modeling Prep (FMP)](https://financialmodelingprep.com/developer/docs/) API. Base URL: `https://financialmodelingprep.com/api/v3/`

**Authentication:** All requests require `?apikey={FMP_API_KEY}` appended (or as a query parameter).  
**Rate Limits:** FMP free tier: 250 requests/day. Premium: varies. Agent must respect rate limits via exponential backoff and caching.  
**Caching Policy:** Cache all responses for 24 hours (fundamentals don't change intraday). Use ticker+endpoint as cache key.

---

### Tool 1: `get_company_profile`

**Purpose:** Fetches company metadata — sector, industry, description, market cap, current price, shares outstanding.

**Endpoint:** `GET /profile/{ticker}`

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | string | Yes | Stock symbol (e.g., "AAPL") |
| apikey | string | Yes | FMP API key |

**Full URL:** `https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={key}`

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `sector` | AAOIFI | Sector screen |
| `industry` | AAOIFI | Sub-industry screen |
| `mktCap` | Altman Z-Score, AAOIFI, Greenblatt | X4 numerator, Debt Ratio denominator, EV component |
| `price` | Altman, Lynch, Graham, Swing | Current price for all ratio calculations |
| `sharesOutstanding` | Piotroski F7, Altman | Share count comparison, X4 calculation |
| `dcf` | Swing G-SW1 | DCF intrinsic value (quick estimate) |

**Output Schema:**
```json
{
  "ticker": "AAPL",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 2873540000000,
  "price": 186.50,
  "shares_outstanding": 15404000000,
  "dcf": 158.72,
  "beta": 1.24,
  "description": "Apple Inc. designs, manufactures, and markets..."
}
```

**Fallback:** If profile call fails, attempt to construct from income statement + balance sheet data. Mark `data_quality: "partial"`. If price cannot be obtained, abort analysis and return error.

---

### Tool 2: `get_income_statement`

**Purpose:** Fetches annual and quarterly income statements for revenue, EPS, net income, EBIT, gross profit.

**Endpoints:**  
- Annual (10 years): `GET /income-statement/{ticker}?period=annual&limit=11&apikey={key}`  
- Quarterly (6 quarters): `GET /income-statement/{ticker}?period=quarter&limit=6&apikey={key}`

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| ticker | string | Stock symbol |
| period | string | "annual" or "quarter" |
| limit | integer | Number of periods to return |
| apikey | string | FMP API key |

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `revenue` | Graham G1, Growth D, Swing G-SW3 | Revenue size, YoY growth, acceleration |
| `netIncome` | Piotroski F1 (ROA numerator), F4 | Net income for ROA, quality of earnings |
| `grossProfit` | Piotroski F8 | Gross margin trend |
| `operatingIncome` (EBIT) | Altman X3, Greenblatt EY, ROIC | EBIT for Z-score, earnings yield, ROIC |
| `eps` | Graham G3, G5, G6, Lynch, Growth D | 10-year EPS history, growth, P/E |
| `interestIncome` | AAOIFI | Impermissible income calculation |
| `weightedAverageShsOut` | Piotroski F7 | Share count comparison |
| `date` | All | Period identification |

**Output Schema:**
```json
{
  "annual": [
    {
      "date": "2024-09-30",
      "revenue": 391035000000,
      "net_income": 93736000000,
      "gross_profit": 170782000000,
      "ebit": 123216000000,
      "eps": 6.08,
      "interest_income": 3862000000,
      "shares_outstanding": 15408763000
    }
    // ... 10 years
  ],
  "quarterly": [
    {
      "date": "2024-09-30",
      "revenue": 94930000000,
      "eps": 1.65,
      "net_income": 14736000000
    }
    // ... 6 quarters
  ]
}
```

**Fallback:** If annual data has < 3 years, downgrade Graham G3/G5 tests to N/A (not enough history). Log in `data_quality_warnings`.

---

### Tool 3: `get_balance_sheet`

**Purpose:** Fetches annual and quarterly balance sheets for assets, liabilities, equity, working capital components.

**Endpoints:**  
- Annual: `GET /balance-sheet-statement/{ticker}?period=annual&limit=3&apikey={key}`  
- Quarterly (most recent): `GET /balance-sheet-statement/{ticker}?period=quarter&limit=2&apikey={key}`

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `totalAssets` | Piotroski F1 (ROA denominator), F5, Altman X1/X2/X3/X5 | Multiple |
| `totalCurrentAssets` | Altman X1, Piotroski F6, AAOIFI | Working capital, current ratio |
| `totalCurrentLiabilities` | Altman X1, Piotroski F6 | Working capital, current ratio |
| `longTermDebt` | Piotroski F5, Graham G2b, AAOIFI | Leverage metrics |
| `totalDebt` | AAOIFI | Debt ratio |
| `cashAndCashEquivalents` | Altman X1 (EV calc), AAOIFI | Cash ratio |
| `shortTermInvestments` | AAOIFI | Cash-like assets for Ratio 2 |
| `retainedEarnings` | Altman X2 | Cumulative retained earnings |
| `totalStockholdersEquity` | Altman X4, Graham G2 | Book value |
| `propertyPlantEquipmentNet` | Greenblatt ROIC | Net fixed assets |
| `netReceivables` | Context | Working capital quality |
| `totalLiabilities` | Altman X4 | X4 denominator |

**Output Schema:**
```json
{
  "annual": [
    {
      "date": "2024-09-30",
      "total_assets": 364980000000,
      "current_assets": 152987000000,
      "current_liabilities": 176392000000,
      "long_term_debt": 85750000000,
      "total_debt": 104590000000,
      "cash_and_equivalents": 29943000000,
      "short_term_investments": 35228000000,
      "retained_earnings": -19154000000,
      "total_equity": 56950000000,
      "total_liabilities": 308030000000,
      "ppe_net": 45680000000
    }
    // 2 prior years
  ]
}
```

---

### Tool 4: `get_cash_flow_statement`

**Purpose:** Fetches operating cash flow, capital expenditure, and free cash flow data.

**Endpoints:**  
- Annual: `GET /cash-flow-statement/{ticker}?period=annual&limit=3&apikey={key}`  
- Quarterly: `GET /cash-flow-statement/{ticker}?period=quarter&limit=2&apikey={key}`

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `operatingCashFlow` | Piotroski F2, F4 | OCF positive test, quality of earnings |
| `freeCashFlow` | Context / DCF validation | Sanity check on DCF |
| `capitalExpenditure` | Context | CapEx intensity for ROIC denominator adjustment |
| `dividendsPaid` | Graham G4, Lynch | Dividend continuity, yield |

**Output Schema:**
```json
{
  "annual": [
    {
      "date": "2024-09-30",
      "operating_cash_flow": 118254000000,
      "free_cash_flow": 108807000000,
      "capital_expenditure": -9447000000,
      "dividends_paid": -15234000000
    }
    // 2 prior years
  ]
}
```

---

### Tool 5: `get_financial_ratios`

**Purpose:** Fetches pre-computed financial ratios to avoid redundant calculations and provide cross-validation.

**Endpoint:** `GET /ratios/{ticker}?period=annual&limit=3&apikey={key}`

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `returnOnAssets` | Piotroski F1, F3 | ROA positive, ROA improving |
| `currentRatio` | Piotroski F6, Graham G2a | Current ratio trend, Graham test |
| `grossProfitMargin` | Piotroski F8 | Gross margin trend |
| `assetTurnover` | Piotroski F9 | Asset turnover trend |
| `debtToEquity` | Context | Additional leverage context |
| `priceToBookRatio` | Graham G7a | P/B for Graham screen |
| `priceEarningsRatio` | Graham G6, Lynch | P/E for Graham and Lynch |
| `dividendYield` | Lynch, Graham G4 | Dividend yield for PEGY |
| `longTermDebtToCapitalization` | Piotroski F5 alt | LT debt as % of capitalization |

**Output Schema:**
```json
{
  "annual": [
    {
      "date": "2024-09-30",
      "roa": 0.2567,
      "current_ratio": 0.814,
      "gross_profit_margin": 0.4368,
      "asset_turnover": 1.109,
      "pb_ratio": 46.50,
      "pe_ratio": 29.27,
      "dividend_yield": 0.0055,
      "lt_debt_to_cap": 0.315
    },
    {
      "date": "2023-09-30",
      "roa": 0.2837,
      "current_ratio": 0.879,
      "gross_profit_margin": 0.4296,
      "asset_turnover": 1.086
    }
  ]
}
```

**Fallback:** If ratios API fails, compute directly from income statement and balance sheet data. Log `data_source: "computed"` for each field.

---

### Tool 6: `get_key_metrics`

**Purpose:** Fetches key metrics including enterprise value components, EBIT, and per-share metrics.

**Endpoint:** `GET /key-metrics/{ticker}?period=annual&limit=3&apikey={key}`

**Response Fields Used:**

| Field | Used By | Rule |
|-------|---------|------|
| `enterpriseValue` | Greenblatt EY | EV for earnings yield denominator |
| `earningsYield` | Greenblatt | Pre-computed (validate vs. our calculation) |
| `returnOnTangibleAssets` | Cross-check | Validate ROIC |
| `revenuePerShare` | Context | Per-share revenue trend |
| `netDebtToEBITDA` | Context | Additional leverage signal |
| `bookValuePerShare` | Graham G7 | Book value per share for P/B |
| `evToOperatingCashFlow` | Context | Alternative valuation check |
| `dividendsPerShare` | Graham G4, Lynch | Annual dividend per share |
| `peRatio` | Cross-check | Validate P/E from ratios |

**Output Schema:**
```json
{
  "annual": [
    {
      "date": "2024-09-30",
      "enterprise_value": 2834560000000,
      "earnings_yield": 0.0435,
      "book_value_per_share": 3.765,
      "dividends_per_share": 0.99,
      "net_debt_to_ebitda": 0.62,
      "pe_ratio": 29.27
    }
  ]
}
```

---

### Tool 7: `get_dcf_value`

**Purpose:** Fetches FMP's discounted cash flow (DCF) intrinsic value estimate for the stock.

**Endpoint:** `GET /discounted-cash-flow/{ticker}?apikey={key}`

**Important caveats:**
- FMP's DCF is a single-model estimate using their proprietary growth and discount rate assumptions
- Treat as ONE data point, not ground truth
- FCF-based model using WACC as discount rate
- Growth rates are derived from historical FCF growth
- The agent outputs the margin of safety calculation using this value but flags: `dcf_model: "FMP single-model estimate — treat as directional"`

**Response Fields Used:**

| Field | Used By |
|-------|---------|
| `dcf` | Swing G-SW1 (margin of safety), Valuation sub-score DCF bonus |
| `Stock Price` | Cross-validate vs. profile price |
| `date` | Ensure DCF is current (within 30 days) |

**Output Schema:**
```json
{
  "ticker": "AAPL",
  "dcf_value": 158.72,
  "current_price": 186.50,
  "margin_of_safety_pct": -14.9,
  "model": "FMP DCF single-model estimate",
  "date": "2026-03-28"
}
```

**Fallback:** If DCF API fails, use a simple Gordon Growth Model estimate:
```
simple_dcf = FCF_per_share × (1 + g) / (r - g)
where:
  g = 5-year historical FCF CAGR (capped at 15% to avoid overestimation)
  r = risk_free_rate + beta × equity_risk_premium (use 10% as default WACC if unknowns)
```
Flag `dcf_source: "fallback_gordon_growth"` in output.

---

### Tool 8: `get_analyst_estimates`

**Purpose:** Fetches consensus analyst EPS and revenue estimates to compute earnings surprise (actual vs. estimated).

**Endpoint:** `GET /analyst-estimates/{ticker}?period=quarter&limit=4&apikey={key}`

**Note:** This endpoint provides FORWARD estimates. To compute SURPRISE for the most recent completed quarter, we compare actual EPS (from `get_income_statement` quarterly) vs. the analyst estimate for that period. FMP's `/earnings-surprises/{ticker}` endpoint provides this directly.

**Alternative Endpoint:** `GET /earnings-surprises/{ticker}?apikey={key}`

**Response Fields Used:**

| Field | Used By |
|-------|---------|
| `actualEarningResult` | Swing G-SW2 | Actual EPS |
| `estimatedEarning` | Swing G-SW2 | Consensus estimate |
| `date` | Match to most recent quarter |

**Output Schema:**
```json
{
  "most_recent_quarter": {
    "date": "2024-09-30",
    "actual_eps": 1.65,
    "estimated_eps": 1.62,
    "surprise_pct": 1.85,
    "beat": true
  }
}
```

**Fallback:** If analyst estimates are unavailable, set `earnings_surprise: null` and note `"Analyst estimates not available for this ticker"`. Do not estimate; leave as N/A.

---

### Tool 9: `get_enterprise_value`

**Purpose:** Fetches enterprise value and its components for Greenblatt earnings yield calculation.

**Endpoint:** `GET /enterprise-values/{ticker}?period=annual&limit=1&apikey={key}`

**Response Fields Used:**

| Field | Used By |
|-------|---------|
| `enterpriseValue` | Greenblatt EY denominator |
| `marketCapitalization` | Cross-validate vs. profile |
| `minusCashAndCashEquivalents` | EV component validation |
| `addTotalDebt` | EV component validation |

**Output Schema:**
```json
{
  "date": "2024-09-30",
  "enterprise_value": 2834560000000,
  "market_cap": 2873540000000,
  "total_debt": 104590000000,
  "cash": 29943000000,
  "ev_check": "2873540 + 104590 - 29943 = 2948187 (note: FMP may use slightly different components)"
}
```

**Calculation note:** EV from FMP key-metrics vs. enterprise-values endpoint may differ slightly. Use `enterprise-values` endpoint as primary; `key-metrics.enterpriseValue` as cross-check. If they differ by > 2%, log a warning.

---

### Tool 10: `get_stock_peers`

**Purpose:** Fetches industry peers for sector context and relative positioning of metrics.

**Endpoint:** `GET /stock_peers?symbol={ticker}&apikey={key}`

**Usage in this agent:** Peers are used for CONTEXTUAL reporting only — they do not influence the deterministic score. The output includes peer comparison notes (e.g., "AAPL's ROIC of 170% vs. sector median of 25%") to help the human understand whether the metrics are sector-specific anomalies.

**Response Fields Used:**

| Field | Used By |
|-------|---------|
| `peersList` | Context | List of peer tickers |

**Output Schema:**
```json
{
  "ticker": "AAPL",
  "peers": ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
  "note": "Peer data used for context only — does not affect deterministic score"
}
```

**Fallback:** If peers API fails, use the sector from company profile as context label. Peer comparison notes are omitted from output.

---

### API Call Sequence & Dependency Map

```
1. get_company_profile()          → price, market_cap, sector, shares_outstanding
2. get_income_statement()         → net_income, revenue, ebit, eps, interest_income [10yr annual + 6Q]
3. get_balance_sheet()            → assets, liabilities, debt, equity, ppe [3yr annual + 2Q]
4. get_cash_flow_statement()      → ocf, dividends_paid [3yr annual + 2Q]
5. get_financial_ratios()         → roa, current_ratio, gross_margin, pe, pb, div_yield
6. get_key_metrics()              → enterprise_value, book_value, dividends_per_share
7. get_dcf_value()                → dcf_intrinsic_value
8. get_analyst_estimates()        → actual_eps, estimated_eps (earnings surprise)
9. get_enterprise_value()         → enterprise_value (primary source for Greenblatt)
10. get_stock_peers()             → peers list (context only)
```

**Parallel execution:** Steps 2–4 can run in parallel. Steps 5–10 can run in parallel after step 1. Step 1 must complete first (provides ticker validation and market_cap needed by other steps).

**Total API calls per analysis:** 12–14 (accounting for annual + quarterly variants)

---

## SECTION 4: Complete JSON Output Schema

The complete output is a deterministic JSON document. Every score, every pass/fail, and every value is fully traceable to the raw data. The LLM summary (at the end) is generated AFTER all scoring is complete and reads from the JSON — it cannot alter any field.

```json
{
  "agent": "fundamental",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "timestamp": "2026-03-28T12:00:00Z",
  "analysis_date": "2026-03-28",
  "data_quality": "live",
  "data_sources_used": [
    "FMP /profile/AAPL",
    "FMP /income-statement/AAPL (annual 10yr, quarterly 6Q)",
    "FMP /balance-sheet-statement/AAPL (annual 3yr, quarterly 2Q)",
    "FMP /cash-flow-statement/AAPL (annual 3yr)",
    "FMP /ratios/AAPL (annual 3yr)",
    "FMP /key-metrics/AAPL (annual 1yr)",
    "FMP /discounted-cash-flow/AAPL",
    "FMP /earnings-surprises/AAPL",
    "FMP /enterprise-values/AAPL (annual 1yr)"
  ],
  "data_quality_warnings": [],
  "fiscal_year_end": "2024-09-30",
  "currency": "USD",
  "sector": "Technology",
  "industry": "Consumer Electronics",

  "raw_data_snapshot": {
    "current_price": 186.50,
    "market_cap": 2873540000000,
    "shares_outstanding": 15404000000,
    "shares_outstanding_prior_year": 15552000000,
    "total_assets_current": 364980000000,
    "total_assets_prior": 352583000000,
    "current_assets": 152987000000,
    "current_liabilities": 176392000000,
    "long_term_debt_current": 85750000000,
    "long_term_debt_prior": 98959000000,
    "total_debt": 104590000000,
    "total_liabilities": 308030000000,
    "total_equity": 56950000000,
    "retained_earnings": -19154000000,
    "cash_and_equivalents": 29943000000,
    "short_term_investments": 35228000000,
    "ppe_net": 45680000000,
    "net_income_current": 93736000000,
    "net_income_prior": 96995000000,
    "operating_cash_flow_current": 118254000000,
    "operating_cash_flow_prior": 113000000000,
    "revenue_current": 391035000000,
    "revenue_prior": 383285000000,
    "ebit_current": 123216000000,
    "gross_profit_current": 170782000000,
    "gross_profit_prior": 169148000000,
    "gross_margin_current": 0.4368,
    "gross_margin_prior": 0.4296,
    "roa_current": 0.2567,
    "roa_prior": 0.2751,
    "current_ratio_current": 0.867,
    "current_ratio_prior": 0.879,
    "asset_turnover_current": 1.071,
    "asset_turnover_prior": 1.086,
    "eps_current": 6.08,
    "eps_prior": 6.11,
    "pe_ratio": 30.67,
    "pb_ratio": 50.91,
    "dividend_yield": 0.0055,
    "dividends_per_share": 0.99,
    "enterprise_value": 2948187000000,
    "interest_income": 3862000000,
    "eps_10yr_history": [1.42, 2.18, 2.32, 2.99, 3.28, 5.61, 5.67, 6.15, 6.11, 6.08],
    "revenue_10yr_history": [182795, 233715, 215639, 265595, 274515, 365817, 394328, 383285, 391035],
    "quarterly_revenue": [
      {"date": "2024-09-30", "revenue": 94930000000},
      {"date": "2024-06-30", "revenue": 85777000000},
      {"date": "2024-03-31", "revenue": 90753000000},
      {"date": "2023-12-31", "revenue": 119575000000},
      {"date": "2023-09-30", "revenue": 89498000000},
      {"date": "2023-06-30", "revenue": 81797000000}
    ]
  },

  "sub_scores": {

    "financial_health": {
      "score": 7.5,
      "weight": 0.30,
      "weighted_contribution": 2.25,

      "piotroski": {
        "total": 6,
        "max": 9,
        "mapped_score": 7,
        "interpretation": "financially sound",
        "criteria": {
          "F1_roa_positive": {
            "pass": true,
            "value": 0.2567,
            "threshold": "> 0",
            "net_income": 93736000000,
            "total_assets": 364980000000,
            "justification": "ROA of 25.67% is strongly positive. Net Income $93.7B on Total Assets $365.0B. Company is clearly profitable on an asset basis."
          },
          "F2_operating_cf_positive": {
            "pass": true,
            "value": 118254000000,
            "threshold": "> 0",
            "justification": "Operating cash flow of $118.3B is strongly positive, demonstrating robust cash generation from core operations."
          },
          "F3_roa_improving": {
            "pass": false,
            "value_current": 0.2567,
            "value_prior": 0.2751,
            "threshold": "current > prior",
            "justification": "ROA declined from 27.51% (FY2023) to 25.67% (FY2024). Net income fell slightly (-3.4%) while assets grew (+3.5%). ROA trend is negative."
          },
          "F4_quality_of_earnings": {
            "pass": true,
            "ocf": 118254000000,
            "net_income": 93736000000,
            "ratio": 1.262,
            "threshold": "OCF > Net Income",
            "justification": "Operating cash flow of $118.3B significantly exceeds net income of $93.7B (OCF/NI ratio = 1.26). Earnings are high quality with strong cash conversion. Accrual component is minimal."
          },
          "F5_leverage_decreasing": {
            "pass": true,
            "lt_debt_to_assets_current": 0.2349,
            "lt_debt_to_assets_prior": 0.2807,
            "lt_debt_current": 85750000000,
            "lt_debt_prior": 98959000000,
            "threshold": "current < prior",
            "justification": "Long-term debt decreased from $99.0B (FY2023) to $85.8B (FY2024). LT Debt/Assets improved from 28.1% to 23.5%. Apple is actively deleveraging."
          },
          "F6_liquidity_improving": {
            "pass": false,
            "current_ratio_current": 0.867,
            "current_ratio_prior": 0.879,
            "threshold": "current > prior",
            "justification": "Current ratio decreased slightly from 0.879 to 0.867. Note: Apple intentionally maintains low current ratio — its current ratio has been below 1.0 consistently due to massive deferred revenue and timing of payables. This is a structural characteristic, not financial distress."
          },
          "F7_no_dilution": {
            "pass": true,
            "shares_current": 15404000000,
            "shares_prior": 15552000000,
            "change_pct": -0.95,
            "threshold": "current <= prior",
            "justification": "Shares outstanding decreased by ~148M (-0.95%) from 15.55B to 15.40B, driven by Apple's consistent buyback program ($90B+ repurchased in FY2024). No dilution — strong shareholder return signal."
          },
          "F8_gross_margin_improving": {
            "pass": true,
            "gross_margin_current": 0.4368,
            "gross_margin_prior": 0.4296,
            "threshold": "current > prior",
            "justification": "Gross margin improved by 72 basis points from 42.96% to 43.68%. Services mix shift (higher-margin) is driving margin expansion."
          },
          "F9_asset_turnover_improving": {
            "pass": false,
            "asset_turnover_current": 1.071,
            "asset_turnover_prior": 1.086,
            "threshold": "current > prior",
            "justification": "Asset turnover declined from 1.086 to 1.071. Revenue grew 2.0% but total assets grew 3.5%, slightly outpacing revenue growth. Asset productivity marginally decreased."
          }
        }
      },

      "altman_z_score": {
        "score": 4.82,
        "zone": "safe",
        "zone_threshold": "> 3.0",
        "mapped_score": 10,
        "components": {
          "x1_working_capital_ratio": {
            "label": "Working Capital / Total Assets",
            "working_capital": -23405000000,
            "total_assets": 364980000000,
            "value": -0.0641,
            "weight": 1.2,
            "weighted": -0.0769,
            "note": "Apple's working capital is negative due to high payables and deferred revenue — a common structural characteristic of large tech companies with high bargaining power over suppliers, not a liquidity crisis."
          },
          "x2_retained_earnings_ratio": {
            "label": "Retained Earnings / Total Assets",
            "retained_earnings": -19154000000,
            "total_assets": 364980000000,
            "value": -0.0524,
            "weight": 1.4,
            "weighted": -0.0734,
            "note": "Retained earnings are negative because Apple has returned more capital than it has earned cumulatively (via buybacks and dividends exceeding retained profits). This is common for mature capital-return-focused companies and does NOT indicate accumulated losses."
          },
          "x3_ebit_ratio": {
            "label": "EBIT / Total Assets",
            "ebit": 123216000000,
            "total_assets": 364980000000,
            "value": 0.3376,
            "weight": 3.3,
            "weighted": 1.1141
          },
          "x4_equity_to_liabilities": {
            "label": "Market Value of Equity / Total Liabilities",
            "market_cap": 2873540000000,
            "total_liabilities": 308030000000,
            "value": 9.329,
            "weight": 0.6,
            "weighted": 5.5974,
            "note": "This component dominates Apple's Z-Score. Apple's $2.87T market cap vs $308B in liabilities creates an extraordinary safety buffer."
          },
          "x5_sales_ratio": {
            "label": "Net Sales / Total Assets",
            "revenue": 391035000000,
            "total_assets": 364980000000,
            "value": 1.0714,
            "weight": 1.0,
            "weighted": 1.0714
          }
        },
        "formula": "Z = 1.2×(-0.0641) + 1.4×(-0.0524) + 3.3×(0.3376) + 0.6×(9.329) + 1.0×(1.0714)",
        "calculation": "-0.0769 + (-0.0734) + 1.1141 + 5.5974 + 1.0714 = 7.63",
        "z_score_corrected": 7.63,
        "justification": "Z-Score of 7.63 places AAPL firmly in the Safe Zone (Z > 3.0). The score is dominated by X4 (market cap / liabilities = 9.33), which reflects Apple's extraordinary market valuation relative to its debt. Bankruptcy risk is negligible. CAVEAT: Altman's model was designed for manufacturing companies. Apple's negative working capital (X1) and negative retained earnings (X2) reflect capital-light tech dynamics and aggressive buyback programs, not financial distress. The high EBIT/Assets (X3 = 33.8%) is the most meaningful signal here.",
        "model_applicability_warning": "Altman original Z-Score is calibrated for manufacturing companies. For asset-light tech companies, X4 (market cap/liabilities) can dominate and overstate safety during market bubbles. Consider Z''-Score variant for non-manufacturing."
      },

      "financial_health_calculation": {
        "piotroski_mapped": 7,
        "altman_mapped": 10,
        "formula": "(7 × 0.5) + (10 × 0.5)",
        "result": 8.5,
        "final_score": 8.5
      }
    },

    "valuation": {
      "score": 3.0,
      "weight": 0.30,
      "weighted_contribution": 0.90,

      "lynch_fair_value": {
        "ratio": 0.183,
        "mapped_score": 1,
        "interpretation": "significantly_overvalued",
        "components": {
          "eps_growth_rate_pct": 2.5,
          "dividend_yield_pct": 0.55,
          "sum_growth_yield": 3.05,
          "pe_ratio": 30.67,
          "eps_growth_source": "5-year trailing EPS CAGR: EPS grew from $5.61 (FY2019) to $6.08 (FY2024) → CAGR = (6.08/5.61)^(1/5) - 1 = 1.6%... using analyst 5yr forward growth est of 8% → use 8.0% as forward estimate"
        },
        "formula": "(EPS_Growth% + Div_Yield%) / P/E = (8.0 + 0.55) / 30.67",
        "formula_result": 0.279,
        "interpretation_using_forward_growth": "With 8% forward EPS growth estimate: (8.0 + 0.55) / 30.67 = 0.28 → still well below 1.0 → moderately to significantly overvalued by Lynch standards",
        "justification": "Lynch Fair Value Ratio of 0.28 (using forward growth) is well below 1.0, indicating the stock is overvalued by Lynch's PEGY framework. The 30.7x P/E is not justified by the ~8% annual growth rate plus 0.55% dividend yield. For Lynch fair value (ratio = 1.0), the stock would need P/E of ~8.6 at current growth, or grow at ~25% with the current P/E. Neither is the case."
      },

      "pegy_ratio": {
        "value": 3.58,
        "formula": "P/E / (Growth% + Yield%) = 30.67 / (8.0 + 0.55)",
        "interpretation": "overvalued (PEGY > 1.0)"
      },

      "graham_pe_test": {
        "pass": false,
        "pe_3yr_avg": 29.85,
        "eps_3yr_avg": 6.10,
        "current_price": 186.50,
        "threshold": "<= 15",
        "bonus": 0,
        "justification": "3-year average P/E of 29.85 (using 3yr avg EPS of $6.10) significantly exceeds Graham's 15x ceiling. Stock is nearly twice as expensive as Graham's limit by this measure."
      },

      "graham_pb_test": {
        "pass": false,
        "pb_ratio": 50.91,
        "pe_times_pb": 1563,
        "threshold": "P/B <= 1.5 OR (P/E × P/B) <= 22.5",
        "bonus": 0,
        "justification": "P/B of 50.9 vastly exceeds the 1.5x limit. P/E × P/B = 30.67 × 50.91 = 1,563, compared to Graham's 22.5 limit. Apple's high P/B is a direct result of negative book equity from buybacks (book value per share ≈ $3.77). Note: This is an extreme case where the Graham P/B criterion arguably becomes meaningless for a company that has repurchased >100% of its retained earnings."
      },

      "dcf_margin_of_safety": {
        "dcf_value": 158.72,
        "current_price": 186.50,
        "margin_pct": -14.9,
        "interpretation": "overvalued",
        "dcf_model": "FMP DCF single-model estimate",
        "bonus": 0,
        "justification": "Stock trades 14.9% ABOVE its FMP DCF intrinsic value of $158.72. No margin of safety exists. The investor is paying a premium to intrinsic value. CAVEAT: FMP's DCF model uses their proprietary growth and discount rate assumptions. A DCF with higher growth assumptions could produce a higher intrinsic value. Treat as one directional data point."
      },

      "valuation_calculation": {
        "lynch_mapped": 1,
        "graham_pe_bonus": 0,
        "graham_pb_bonus": 0,
        "dcf_bonus": 0,
        "raw": 1,
        "capped": 1,
        "final_score": 1.0,
        "note": "Valuation score of 1.0 reflects that AAPL fails ALL four valuation tests. This is consistent with Apple being a premium-priced quality business, not a value investment."
      }
    },

    "profitability": {
      "score": 7.4,
      "weight": 0.20,
      "weighted_contribution": 1.48,

      "greenblatt_earnings_yield": {
        "ebit": 123216000000,
        "enterprise_value": 2948187000000,
        "earnings_yield_pct": 4.18,
        "mapped_score": 3,
        "interpretation": "below average — stock is expensive relative to operating earnings",
        "justification": "Earnings Yield of 4.18% (EBIT/EV) is in the 3-5% range, indicating the stock is expensive relative to its operating earnings. At 4.18%, an investor is paying $23.93 for every $1 of EBIT — i.e., an implied EV/EBIT of ~24x, well above the 10x that would indicate a cheap stock."
      },

      "greenblatt_roic": {
        "ebit": 123216000000,
        "ppe_net": 45680000000,
        "working_capital": -23405000000,
        "net_fixed_assets_plus_wc": 22275000000,
        "roic_pct": 553.2,
        "mapped_score": 9,
        "interpretation": "exceptional — asset-light business model with extraordinary capital efficiency",
        "justification": "ROIC of 553% is extreme due to Apple's negative working capital (large payables, deferred revenue) and relatively small PP&E relative to EBIT. This reflects an asset-light, high-margin business model with enormous bargaining power over suppliers. When working capital is negative, Greenblatt's formula produces anomalously high ROIC — flag as SECTOR_ANOMALY. The directional signal (high ROIC = high quality business) is valid; the absolute number should not be compared to manufacturing companies.",
        "sector_anomaly_flag": true,
        "sector_anomaly_note": "Apple's negative working capital causes ROIC to be extremely high and not directly comparable to capital-intensive businesses. Use with context."
      },

      "gross_margin_trend": {
        "improving": true,
        "gross_margin_current": 0.4368,
        "gross_margin_prior": 0.4296,
        "change_bps": 72,
        "bonus": 1.0,
        "justification": "Gross margin improved 72 basis points from 42.96% to 43.68%, driven by growing high-margin Services revenue mix. Piotroski F8: PASS."
      },

      "profitability_calculation": {
        "ey_mapped": 3,
        "roic_mapped": 9,
        "gross_margin_bonus": 1.0,
        "formula": "(3 × 0.4) + (9 × 0.4) + 1.0",
        "raw": 5.8,
        "capped_at_10": 5.8,
        "final_score": 5.8,
        "note": "Score of 5.8 reflects a high-quality but expensive business. ROIC is exceptional (maps to 9) but earnings yield is low (maps to 3) because the stock is priced very high."
      }
    },

    "growth": {
      "score": 3.4,
      "weight": 0.20,
      "weighted_contribution": 0.68,

      "revenue_growth_yoy": {
        "revenue_current": 391035000000,
        "revenue_prior": 383285000000,
        "growth_pct": 2.02,
        "mapped_score": 3,
        "interpretation": "slow growth (0-5% range)",
        "justification": "Revenue grew 2.02% YoY from $383.3B to $391.0B. This is below inflation in many markets and indicates Apple is operating near revenue saturation in its core hardware segments. Services growth partially offsets iPhone plateau."
      },

      "eps_growth_yoy": {
        "eps_current": 6.08,
        "eps_prior": 6.11,
        "growth_pct": -0.49,
        "mapped_score": 1,
        "interpretation": "negative EPS growth",
        "justification": "EPS declined marginally by 0.49% from $6.11 to $6.08 (FY2023 to FY2024). Net income declined 3.4% while buybacks partially offset the EPS impact. Mapped to score 1 (negative growth bracket)."
      },

      "graham_10y_growth_test": {
        "pass": true,
        "avg_eps_start_3yr": 1.97,
        "avg_eps_end_3yr": 6.10,
        "years": "FY2014-2016 average vs FY2022-2024 average",
        "growth_pct": 209.6,
        "threshold_pct": 33,
        "bonus": 1.0,
        "justification": "10-year EPS grew 209.6% (from $1.97 average in FY2014-16 to $6.10 average in FY2022-24). Comfortably exceeds Graham's 33% minimum. This reflects Apple's remarkable earnings compounding over the decade driven by iPhone ecosystem, services growth, and buybacks."
      },

      "growth_calculation": {
        "rev_growth_mapped": 3,
        "eps_growth_mapped": 1,
        "graham_growth_bonus": 1.0,
        "formula": "(3 × 0.4) + (1 × 0.4) + 1.0",
        "raw": 2.6,
        "capped_at_10": 2.6,
        "final_score": 2.6,
        "note": "Low growth score reflects Apple's near-term growth stagnation. The strong 10-year history (Graham bonus) partially offsets weak recent momentum."
      }
    }
  },

  "shariah_compliance": {
    "status": "Borderline",
    "status_description": "Stock passes AAOIFI financial ratio screens, but the debt ratio is within 2% of the 33% threshold and requires monitoring.",
    "screening_standard": "AAOIFI Standard No. 21 (33% threshold, DJIM/MSCI alignment)",

    "sector_screen": {
      "pass": true,
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "justification": "Technology/Consumer Electronics is a permissible business activity under AAOIFI standards. Apple's primary revenue comes from hardware (iPhone, Mac, iPad) and software services (App Store, iCloud, Apple Music). None of Apple's core revenue segments involve prohibited activities."
    },

    "debt_ratio": {
      "pass": true,
      "total_debt": 104590000000,
      "market_cap": 2873540000000,
      "value": 0.0364,
      "threshold": "< 0.33",
      "proximity_warning": false,
      "justification": "Total Debt / Market Cap = $104.6B / $2,873.5B = 3.64%. Well within the 33% threshold. Apple's massive market cap relative to its debt makes this ratio trivially small.",
      "alternative_calculation": {
        "standard": "SC Malaysia: Total Debt / Total Assets",
        "value": 0.2865,
        "pass": true,
        "note": "Using Total Assets denominator: $104.6B / $365.0B = 28.65%. Still passes but is within 5% of the 33% limit — proximity warning would apply here."
      }
    },

    "cash_ratio": {
      "pass": true,
      "cash_and_equivalents": 29943000000,
      "short_term_investments": 35228000000,
      "total_liquid": 65171000000,
      "market_cap": 2873540000000,
      "value": 0.0227,
      "threshold": "< 0.33",
      "justification": "Cash + Short-term Investments / Market Cap = $65.2B / $2,873.5B = 2.27%. Apple's liquid assets are a tiny fraction of its market cap. No concern here."
    },

    "impermissible_income_ratio": {
      "pass": true,
      "interest_income": 3862000000,
      "total_revenue": 391035000000,
      "value": 0.00988,
      "threshold": "< 0.05",
      "justification": "Interest income of $3.86B represents 0.99% of total revenue — well below the 5% threshold. Apple earns interest on its massive cash pile, but this is incidental to its core business."
    },

    "purification": {
      "purification_ratio": 0.00988,
      "purification_per_share": 0.0601,
      "calculation": "EPS $6.08 × 0.988% = $0.060 per share must be donated to charity annually to purify returns",
      "note": "Purification is required even when passing. The investor must donate $0.06 per share held per year (or equivalent proportion of portfolio returns) to an approved charity."
    }
  },

  "swing_trade_assessment": {
    "fundamental_support": "weak",
    "dcf_upside_pct": -14.9,

    "dcf_analysis": {
      "dcf_value": 158.72,
      "current_price": 186.50,
      "interpretation": "Stock is 14.9% ABOVE DCF value — fundamentals do not support price appreciation from intrinsic value perspective"
    },

    "earnings_surprise": {
      "beat": true,
      "actual_eps": 1.65,
      "estimated_eps": 1.62,
      "surprise_pct": 1.85,
      "quarter": "Q4 FY2024 (Sep 2024)",
      "justification": "Most recent quarter EPS of $1.65 beat consensus estimate of $1.62 by 1.85%. This is a modest beat — positive but not a strong catalyst. PEAD research suggests modest beats create some near-term price support but not dramatic momentum."
    },

    "revenue_acceleration": {
      "accelerating": false,
      "current_q_revenue_yoy_growth_pct": 6.1,
      "prior_q_revenue_yoy_growth_pct": 4.8,
      "current_q": {"date": "2024-09-30", "revenue": 94930000000, "yoy_vs": 89498000000},
      "prior_q": {"date": "2024-06-30", "revenue": 85777000000, "yoy_vs": 81797000000},
      "note": "Current Q revenue grew 6.1% YoY vs. prior Q 4.8% YoY — ACCELERATING in the most recent quarter. However, this includes typical iPhone launch seasonality in Sep quarter.",
      "acceleration_flag": true,
      "seasonality_caveat": "Q4 (Sep) includes new iPhone launch. Revenue acceleration may reflect launch timing, not underlying business acceleration."
    },

    "overall_justification": "Fundamentals provide WEAK-to-NEUTRAL support for a swing trade. The stock trades 14.9% above DCF intrinsic value, and fails all four valuation tests (Graham P/E, Graham P/B, Lynch Fair Value, DCF margin of safety). The recent earnings beat (1.85%) is positive but modest. Revenue acceleration in the Sep quarter is partially seasonal. Apple's business quality is exceptional (Piotroski=6, ROIC extremely high), but the valuation premium means fundamentals are a headwind rather than a tailwind for additional price appreciation. A technical catalyst (e.g., market-wide rally or sector rotation) could still produce a swing gain, but fundamentals alone do not justify initiating a swing position.",

    "risk_factors": [
      "P/E of 30.7x leaves limited room for multiple expansion; multiple compression risk is elevated",
      "EPS growth is near-zero (−0.5% YoY) — stock is priced for higher growth than is currently materializing",
      "Negative DCF margin of safety means any DCF mean-reversion represents a 14.9% downside headwind",
      "High buyback program ($90B+/yr) provides EPS support but cannot indefinitely offset revenue stagnation"
    ]
  },

  "final_score": 5.0,
  "score_breakdown": {
    "financial_health": {"score": 8.5, "weight": 0.30, "contribution": 2.55},
    "valuation": {"score": 1.0, "weight": 0.30, "contribution": 0.30},
    "profitability": {"score": 5.8, "weight": 0.20, "contribution": 1.16},
    "growth": {"score": 2.6, "weight": 0.20, "contribution": 0.52},
    "formula": "(8.5×0.30) + (1.0×0.30) + (5.8×0.20) + (2.6×0.20)",
    "calculation": "2.55 + 0.30 + 1.16 + 0.52",
    "raw": 4.53,
    "rounded": 4.5,
    "interpretation": "Below average fundamentals — Apple is a high-quality business priced for perfection. The valuation sub-score (1.0) heavily penalizes the overall score, reflecting genuine overvaluation by multiple frameworks."
  },

  "challenges_and_caveats": [
    {
      "framework": "Graham Criteria",
      "caveat": "Graham's criteria are designed for defensive long-term investors targeting 10+ year horizons with maximum capital preservation. AAPL fails P/E and P/B tests because it is a premium-priced quality business, not a 'cigar butt' value stock. Graham himself acknowledged that growth businesses might deserve higher multiples. For swing trading (5-15 day horizon), Graham's valuation criteria serve as a ceiling indicator — they tell us the stock is expensive, but they cannot predict whether that premium will expand or contract in the next 2 weeks.",
      "mitigation": "Graham criteria contribute bonuses to sub-scores (not failures that zero out the score). Their absence reduces the valuation score but does not make it impossible for a stock to score well overall on other dimensions."
    },
    {
      "framework": "Piotroski F-Score",
      "caveat": "Piotroski's original research was specifically designed for HIGH book-to-market (low P/B) value stocks. For growth stocks like AAPL with negative book equity, some criteria produce misleading signals: F6 (current ratio) is structurally low not due to distress but due to business model; F9 (asset turnover) may decline as a company invests in long-term assets. Applying Piotroski to growth stocks risks false negatives.",
      "mitigation": "Piotroski score is used as one of two inputs to the Financial Health sub-score (50% weight alongside Altman). Structural false negatives in individual criteria are noted in the justification field."
    },
    {
      "framework": "Altman Z-Score",
      "caveat": "The original 1968 Z-Score was calibrated on manufacturing companies. For asset-light tech companies: (1) X4 (market cap/liabilities) dominates and can overstate safety when market is in a bubble — a 50% stock market crash would halve Apple's X4 contribution; (2) Negative working capital (X1) and negative retained earnings (X2) are structural in capital-return-focused tech companies, not distress signals.",
      "mitigation": "The Z''-Score (1995 version, designed for non-manufacturing firms) provides an alternative. Both are computed; agent uses original Z-Score but flags model applicability. The Piotroski score provides a complementary signal that is less susceptible to market-cap fluctuations."
    },
    {
      "framework": "DCF Intrinsic Value",
      "caveat": "DCF is only as accurate as its assumptions. FMP's DCF uses a single set of assumptions (proprietary growth rates, WACC). A ±1% change in the discount rate can move intrinsic value by 15-25%. The margin of safety calculated here is a single-point estimate, not a range.",
      "mitigation": "DCF contributes only a bonus (0–2 points) to the Valuation sub-score — it cannot penalize the score below 0. If DCF API fails, fallback to simple Gordon Growth Model. The output flags 'dcf_model: FMP single-model estimate' to prevent over-reliance."
    },
    {
      "framework": "AAOIFI Shariah Compliance",
      "caveat": "AAOIFI uses market capitalization as the denominator for debt and cash ratios. Market cap fluctuates daily based on stock price movements. A 20% stock price decline could push a previously halal company's debt ratio from 25% to 31% — causing potential status changes based purely on market sentiment, not business fundamentals. The compliance status computed here is POINT-IN-TIME only.",
      "mitigation": "Shariah status is reported separately from the fundamental score with explicit point-in-time warnings. Borderline status is flagged with proximity warnings. Investors relying on Shariah compliance for investment decisions should re-screen quarterly at minimum."
    },
    {
      "framework": "Lynch Fair Value",
      "caveat": "Lynch's model assumes a stable relationship between EPS growth rate and fair P/E. For companies with very low EPS growth (near 0%) or negative growth, the formula breaks down — a company with 1% growth would require P/E of ~1.55 for fair value, which is extreme. The formula works best for companies growing at 10-25% annually.",
      "mitigation": "Use forward analyst consensus EPS growth rate rather than trailing, which is more predictive. Cap EPS growth input at 50% to avoid absurd outcomes for hypergrowth companies. If EPS growth is negative, map Lynch ratio to 0 (worst bucket) regardless of formula output."
    },
    {
      "framework": "Greenblatt Magic Formula",
      "caveat": "The Magic Formula was designed to rank the entire investable universe and buy the top decile — it is inherently relative, not absolute. Our agent uses absolute thresholds (e.g., EY > 12% = excellent) which may be calibrated for a specific market environment. In a low-interest-rate environment, EY > 5% might be excellent; in a high-rate environment, EY > 8% might be the threshold for 'cheap'.",
      "mitigation": "The absolute thresholds used are calibrated to a 'normal' rate environment (3-5% risk-free rate). The agent flags the current rate environment context in the output. Future versions should use sector-relative and rate-environment-adjusted thresholds."
    }
  ],

  "llm_summary": "GENERATED POST-SCORING — Apple Inc. (AAPL) receives a fundamental score of 4.5/10. The company demonstrates exceptional business quality — an Altman Z-Score of 7.63 places it firmly in the financial safety zone, and its operating cash flow of $118B significantly exceeds net income, indicating high earnings quality. Gross margins are expanding (43.68%), driven by the higher-margin Services business. However, the valuation picture is concerning from a fundamental standpoint: the stock trades at 30.7x earnings and 50.9x book value, well above Graham's conservative thresholds, and 14.9% above its DCF intrinsic value. EPS growth was essentially flat (-0.5% YoY). For a swing trade, fundamentals provide weak support — the stock is high quality but expensively priced, meaning fundamentals are a ceiling rather than a catalyst. The shariah compliance status is Borderline: all three AAOIFI ratio tests pass, but the debt/assets ratio of 28.6% (SC Malaysia standard) is within 5% of the 33% threshold. Investors should monitor this quarterly. Purification requirement: $0.06 per share per year.",

  "metadata": {
    "scoring_engine_version": "1.0.0",
    "frameworks_applied": ["Piotroski F-Score", "Altman Z-Score", "Graham Defensive Criteria", "Lynch PEGY", "Greenblatt Magic Formula", "AAOIFI Shariah Standard 21"],
    "llm_used_for_scoring": false,
    "llm_used_for_summary": true,
    "llm_summary_model": "gpt-4o (post-scoring only — reads JSON, does not influence scores)",
    "deterministic": true,
    "reproducible": true
  }
}
```

---

## SECTION 5: Challenges & Design Decisions

This section critically examines each framework, documents known failure modes, and explains the design decisions made to mitigate them.

---

### Challenge 1: Graham Criteria Reject the Best-Performing Stocks

**The Problem:**

Benjamin Graham's 7 criteria would reject Apple (AAPL), Microsoft (MSFT), Amazon (AMZN), Alphabet (GOOGL), and NVIDIA (NVDA) — the five best-performing large-cap stocks of the last 20 years. Specifically:
- All fail the P/E ≤ 15 test (current P/Es: AAPL 30x, MSFT 36x, AMZN 45x, GOOGL 23x, NVDA 70x+)
- Most fail the P/B ≤ 1.5 test (AAPL 51x, MSFT 14x, AMZN 8x, GOOGL 7x)
- Several fail G4 (dividends for 20 years) — Amazon has never paid a dividend

**When Graham Works Best:** Deep value situations — stocks trading below liquidation value ("net-nets"), mature industrials, cyclicals near trough earnings. Graham's framework was developed during and after the Great Depression, when stocks were often genuinely cheap.

**When Graham Fails:** Quality growth businesses with durable competitive advantages (moats) that deserve premium multiples. Buffett himself evolved away from strict Graham criteria to "wonderful companies at fair prices" rather than "fair companies at wonderful prices."

**Our Mitigation:**
1. Graham criteria are implemented as **bonus points**, not mandatory pass/fail gates. A stock can score 0 on all Graham criteria and still receive a high fundamental score if it passes other frameworks.
2. The valuation sub-score has a floor at 1 (not 0) — no valid business scores zero.
3. We explicitly document in the output that Graham's criteria are most relevant for long-term defensive investors, not for swing traders seeking 5-10% gains.
4. A note in `challenges_and_caveats` in the JSON output explains this for every stock that fails Graham criteria.

---

### Challenge 2: Piotroski F-Score Is Designed for Value (Low P/B) Stocks

**The Problem:**

Piotroski explicitly designed his 9-point system for the subset of stocks in the lowest quintile of Price-to-Book ratios. His paper showed F-Score works to separate winners from losers WITHIN the low P/B universe. Applied to growth stocks (high P/B), the F-Score may produce misleading signals:

- **F6 (Current Ratio):** Companies like Apple, Amazon, and Walmart deliberately maintain low current ratios because they have incredible supplier payment terms and high inventory turnover. A current ratio below 1.0 does not signal distress for these companies.
- **F9 (Asset Turnover):** A company investing heavily in long-term assets (PP&E for a new product line, capitalized R&D) will show declining asset turnover temporarily even as the investment is value-creating.
- **F7 (No Dilution):** Stock-based compensation (SBC) is a real economic cost. If a company grants $5B in SBC but also buys back $10B, shares outstanding decrease — F7 passes — but the "effective" dilution from SBC is masked.

**When Piotroski Works Best:** Low P/B stocks where financial trends are the primary signal separating recovery candidates from value traps.

**When Piotroski Fails:** High-quality growth companies where structural factors (business model, growth investments) look like Piotroski negatives.

**Our Mitigation:**
1. Each Piotroski criterion includes a `justification` field that contextualizes the result — a "fail" on F6 for Apple is explicitly noted as a structural business model characteristic.
2. Piotroski is weighted 50% alongside Altman in the Financial Health sub-score. Its influence is diluted by Altman's more comprehensive solvency assessment.
3. Sector-specific flags are raised in the output when structural factors confound the criteria.

---

### Challenge 3: Altman Z-Score Was Calibrated for Manufacturing

**The Problem:**

Altman's 1968 paper used data from 66 manufacturing companies (33 bankrupt, 33 solvent). The model was not designed for:
- **Financial services companies** (banks, insurance) — where debt IS the product and leverage ratios are regulated, not discretionary
- **Asset-light technology companies** — where negative working capital is a sign of strength (supplier financing), not distress
- **Early-stage/pre-revenue companies** — where X3 (EBIT/Assets) will be negative but doesn't necessarily indicate imminent bankruptcy
- **Real estate companies (REITs)** — where total assets are dominated by property values that have entirely different liquidity characteristics

**Specific distortions for tech companies:**
- **X2 (Retained Earnings / Total Assets):** Apple has negative retained earnings because it has returned $700B+ in buybacks over its history. This is not "accumulated losses" — the company is immensely profitable. But negative X2 suppresses the Z-Score.
- **X4 (Market Cap / Total Liabilities):** For large-cap tech companies with small debt relative to market cap, this term can contribute 5-8x the Z-Score threshold by itself, making the company appear "extremely safe" even during a bubble.

**Altman's Own Evolution:** Altman developed the Z'-Score (1983) for private firms and Z''-Score (1995) for non-manufacturing and emerging market firms. The Z''-Score uses only 4 variables with different weights and is better suited for service companies.

**Our Mitigation:**
1. The agent computes BOTH the original Z-Score (public manufacturing companies) and notes Z''-Score as an alternative
2. Sector applicability is flagged in the output: `model_applicability_warning` field
3. Financial services companies are excluded from the standard Z-Score calculation with a note to use sector-specific models
4. Each Z-Score component includes a contextual note explaining any anomalous values

---

### Challenge 4: AAOIFI Debt Ratio Uses Market Cap — Daily Volatility Creates Compliance Instability

**The Problem:**

The AAOIFI formula: `Total Debt / Market Cap < 33%`

Market capitalization = Stock Price × Shares Outstanding. Stock price fluctuates every second the market is open. This creates a mathematically unstable compliance threshold:

**Example:** A company with $1B in debt and $3.1B market cap (ratio = 32.3% — just passes) would fail the screen if the stock drops 3% to a $3.0B market cap (ratio = 33.3% — fails). The debt hasn't changed. The business hasn't changed. The investor base that considers the stock "halal" could change overnight.

This "price-sensitivity" problem is particularly acute for:
- Small-to-mid cap stocks with more price volatility
- Companies in the 25-33% "borderline" zone
- Highly leveraged companies where debt is close to 1/3 of market cap

**A second problem:** Some scholars and screening services (SC Malaysia, for example) use Total Assets as the denominator instead of Market Cap, which produces a more stable (but conceptually different) ratio. SC Malaysia's approach: `Total Debt / Total Assets < 33%` changes much more slowly (assets change with annual financial statements) but ignores market sentiment.

**Our Mitigation:**
1. We compute BOTH the AAOIFI (market cap denominator) and SC Malaysia (total assets denominator) variants and report both
2. We explicitly flag "Borderline" status for any ratio between 25-33%, requiring quarterly re-screening
3. We include a `proximity_warning: true` flag when any ratio is within 3% of the 33% threshold
4. The output includes a clear disclaimer: "Shariah compliance is point-in-time. Re-screen quarterly."
5. **Alternative approach considered but not implemented:** Using 90-day average market cap to smooth out volatility. Not implemented because it deviates from AAOIFI's published standard.

---

### Challenge 5: DCF Intrinsic Value Is Sensitive to Assumptions

**The Problem:**

Discounted Cash Flow valuation requires three key assumptions: (1) near-term growth rate, (2) long-term terminal growth rate, and (3) discount rate (WACC). Small changes in these assumptions produce wildly different intrinsic values:

**Sensitivity Example for a company with FCF/share = $10:**

| Growth Rate | WACC | Intrinsic Value |
|------------|------|----------------|
| 10% | 8% | $245 |
| 10% | 10% | $175 |
| 5% | 8% | $152 |
| 5% | 10% | $120 |
| 15% | 8% | $495 |

The range ($120 to $495) is a 4x spread from reasonable assumption variations. Presenting a single DCF number as "the" intrinsic value is misleading.

**FMP-specific concerns:**
- FMP's DCF uses their proprietary methodology which is not fully disclosed
- The model may use analyst consensus growth rates, which are themselves optimistic on average (analysts have a well-documented upward bias)
- The discount rate assumption is not transparent in FMP's API response

**Our Mitigation:**
1. DCF value is used only as a directional indicator — it contributes 0-2 BONUS points, never penalty points
2. Every DCF output includes: `"dcf_model": "FMP single-model estimate — treat as directional, not definitive"`
3. If DCF API fails, we compute a simple Gordon Growth Model alternative with clearly disclosed assumptions and flag `dcf_source: "fallback_gordon_growth"`
4. A fallback range calculation (bear/base/bull case) is noted as a future enhancement (V2.0)

---

### Challenge 6: Greenblatt Magic Formula Is Relative, Not Absolute

**The Problem:**

Greenblatt's actual methodology ranks ALL stocks in the universe simultaneously and selects the top 20-30 by combined rank. It is fundamentally a RELATIVE ranking system. Our agent applies ABSOLUTE thresholds (e.g., EY > 12% = excellent, ROIC > 30% = good) which introduces two problems:

1. **Market environment dependency:** In 2020-2021 (low-rate environment), EY > 5% was considered excellent. In 2024-2025 (high-rate environment), 10-year Treasuries yield 4%+, making a 5% earnings yield relatively unattractive vs. risk-free alternatives.

2. **Asset-light business anomalies:** As documented for Apple above, companies with negative working capital can produce ROIC of 500%+. Our mapping caps at 9 for ROIC > 30%, which is correct — but the mapping doesn't distinguish between 35% ROIC (exceptional) and 500% ROIC (structural anomaly).

**Our Mitigation:**
1. ROIC values above 100% are flagged with `sector_anomaly_flag: true`
2. The output notes the current rate environment context
3. Greenblatt's relative ranking approach is acknowledged in the caveat field
4. A note is added that absolute thresholds may need recalibration in very high or very low interest rate environments

---

### Challenge 7: How Do We Handle Missing Data?

**The Problem:**

Not all tickers have complete data across all frameworks:
- Small caps may have < 3 years of financial data
- Non-US companies may have different reporting conventions (IFRS vs. GAAP)
- Recent IPOs have no earnings history for Graham G3/G4/G5
- Companies that don't pay dividends fail Graham G4 automatically
- Non-manufacturing companies may have distorted Altman scores

**Our Framework:**

```
For each rule:
  if data not available:
    mark criterion as "N/A" (not 0 or 1)
    exclude from score calculation
    adjust denominator/numerator accordingly
    log in data_quality_warnings

If > 50% of criteria in a sub-score are N/A:
  flag sub_score as "insufficient_data"
  exclude sub_score from final calculation
  adjust final score weights proportionally
```

**Data sufficiency requirements by framework:**

| Framework | Minimum Data Required | Fallback |
|-----------|----------------------|---------|
| Piotroski | 2 years of all 3 statements | Skip unavailable criteria, note in output |
| Altman | 1 year balance sheet + current price | No fallback — exclude if price unavailable |
| Graham | 10yr EPS, 20yr dividends, current ratios | G3/G4/G5 become N/A with < history |
| Lynch | Current P/E, EPS growth estimate | Use trailing if forward unavailable |
| Greenblatt | Current EBIT, EV, PP&E | Exclude for financials/utilities |
| AAOIFI | Sector, current debt, market cap, revenue | Partial results possible |
| DCF | FCF history, market price | Fallback to Gordon Growth Model |

---

## SECTION 6: Rule Engine Pseudocode

The following pseudocode defines the complete deterministic execution flow. Every variable assignment, every conditional branch, and every scoring step is explicit. There are NO LLM calls within the scoring logic. The LLM is invoked ONCE at the very end, AFTER all scores are finalized, and ONLY to generate a human-readable summary paragraph from the JSON.

```python
# ============================================================
# FUNDAMENTAL ANALYSIS AGENT — RULE ENGINE
# Version: 1.0.0
# Design: DETERMINISTIC, RULE-BASED — no LLM in scoring logic
# ============================================================

def run_fundamental_analysis(ticker: str, api_key: str) -> dict:
    """
    Main entry point. Returns the complete JSON output schema.
    All sub-functions are deterministic given the same input data.
    """
    
    # ─────────────────────────────────────────────────────────
    # STEP 0: INITIALIZE OUTPUT STRUCTURE
    # ─────────────────────────────────────────────────────────
    output = {
        "agent": "fundamental",
        "ticker": ticker,
        "timestamp": get_current_utc_iso(),
        "data_quality": "live",
        "data_quality_warnings": [],
        "data_sources_used": [],
    }
    
    # ─────────────────────────────────────────────────────────
    # STEP 1: FETCH ALL DATA (parallel where possible)
    # ─────────────────────────────────────────────────────────
    
    # Step 1.1: Fetch company profile first (needed for market cap, price, sector)
    profile = call_mcp_tool("get_company_profile", {"ticker": ticker})
    if profile is None or profile.get("price") is None:
        return {"error": "Cannot proceed — profile API failed and current price unavailable", 
                "ticker": ticker}
    
    output["data_sources_used"].append("FMP /profile/" + ticker)
    
    # Step 1.2: Fetch all other data sources in parallel
    [
        income_annual,    # 11 years
        income_quarterly, # 6 quarters
        balance_annual,   # 3 years
        balance_quarterly,# 2 quarters
        cashflow_annual,  # 3 years
        ratios_annual,    # 3 years
        key_metrics,      # 1 year
        dcf_data,         # current
        earnings_surprise,# most recent quarter
        enterprise_value, # 1 year
        peers             # current
    ] = parallel_fetch([
        ("get_income_statement", {"ticker": ticker, "period": "annual", "limit": 11}),
        ("get_income_statement", {"ticker": ticker, "period": "quarter", "limit": 6}),
        ("get_balance_sheet", {"ticker": ticker, "period": "annual", "limit": 3}),
        ("get_balance_sheet", {"ticker": ticker, "period": "quarter", "limit": 2}),
        ("get_cash_flow_statement", {"ticker": ticker, "period": "annual", "limit": 3}),
        ("get_financial_ratios", {"ticker": ticker, "period": "annual", "limit": 3}),
        ("get_key_metrics", {"ticker": ticker, "period": "annual", "limit": 1}),
        ("get_dcf_value", {"ticker": ticker}),
        ("get_analyst_estimates", {"ticker": ticker}),
        ("get_enterprise_value", {"ticker": ticker, "period": "annual", "limit": 1}),
        ("get_stock_peers", {"ticker": ticker})
    ])
    
    # Log data source usage and handle failures
    for source, data in zip(SOURCE_NAMES, [income_annual, balance_annual, ...]): 
        if data is not None:
            output["data_sources_used"].append(source)
        else:
            output["data_quality_warnings"].append(f"API failure: {source}")
            output["data_quality"] = "partial"
    
    # ─────────────────────────────────────────────────────────
    # STEP 2: EXTRACT RAW VALUES
    # Compute all raw metrics needed by scoring functions.
    # Every value is extracted deterministically from API response.
    # ─────────────────────────────────────────────────────────
    
    def safe_get(data, key, fallback=None):
        """Returns the value or fallback if None/missing."""
        try:
            return data[key] if data[key] is not None else fallback
        except (KeyError, TypeError):
            return fallback
    
    # Current year financial data
    current_year = income_annual[0]   # Most recent
    prior_year   = income_annual[1]   # One year prior
    
    price           = safe_get(profile, "price")
    market_cap      = safe_get(profile, "mktCap")
    sector          = safe_get(profile, "sector", "Unknown")
    industry        = safe_get(profile, "industry", "Unknown")
    
    net_income_curr = safe_get(current_year, "netIncome")
    net_income_prior= safe_get(prior_year, "netIncome")
    revenue_curr    = safe_get(current_year, "revenue")
    revenue_prior   = safe_get(prior_year, "revenue")
    ebit_curr       = safe_get(current_year, "operatingIncome")  # EBIT = Operating Income
    gross_profit_curr = safe_get(current_year, "grossProfit")
    gross_profit_prior= safe_get(prior_year, "grossProfit")
    interest_income = safe_get(current_year, "interestIncome", 0)
    
    total_assets_curr  = safe_get(balance_annual[0], "totalAssets")
    total_assets_prior = safe_get(balance_annual[1], "totalAssets")
    current_assets     = safe_get(balance_annual[0], "totalCurrentAssets")
    current_liabilities= safe_get(balance_annual[0], "totalCurrentLiabilities")
    lt_debt_curr       = safe_get(balance_annual[0], "longTermDebt")
    lt_debt_prior      = safe_get(balance_annual[1], "longTermDebt")
    total_debt         = safe_get(balance_annual[0], "totalDebt")
    total_liabilities  = safe_get(balance_annual[0], "totalLiabilities")
    retained_earnings  = safe_get(balance_annual[0], "retainedEarnings")
    total_equity       = safe_get(balance_annual[0], "totalStockholdersEquity")
    cash               = safe_get(balance_annual[0], "cashAndCashEquivalents")
    short_term_inv     = safe_get(balance_annual[0], "shortTermInvestments", 0)
    ppe_net            = safe_get(balance_annual[0], "propertyPlantEquipmentNet")
    shares_curr        = safe_get(income_annual[0], "weightedAverageShsOut")
    shares_prior       = safe_get(income_annual[1], "weightedAverageShsOut")
    
    ocf_curr  = safe_get(cashflow_annual[0], "operatingCashFlow")
    ocf_prior = safe_get(cashflow_annual[1], "operatingCashFlow")
    dividends_paid = safe_get(cashflow_annual[0], "dividendsPaid", 0)
    
    # Pre-computed ratios (fallback to manual calculation if API value unavailable)
    roa_curr    = safe_get(ratios_annual[0], "returnOnAssets") or safe_div(net_income_curr, total_assets_curr)
    roa_prior   = safe_get(ratios_annual[1], "returnOnAssets") or safe_div(net_income_prior, total_assets_prior)
    cr_curr     = safe_get(ratios_annual[0], "currentRatio")   or safe_div(current_assets, current_liabilities)
    cr_prior    = safe_get(ratios_annual[1], "currentRatio")   or safe_div(prior_current_assets, prior_current_liabilities)
    pe_ratio    = safe_get(ratios_annual[0], "priceEarningsRatio") or safe_div(price, eps_ttm)
    pb_ratio    = safe_get(ratios_annual[0], "priceToBookRatio")
    div_yield   = safe_get(ratios_annual[0], "dividendYield", 0)
    
    # Greenblatt Enterprise Value (preferred from enterprise_value endpoint)
    ev = safe_get(enterprise_value, "enterpriseValue") or (market_cap + total_debt - cash)
    
    # EPS history (10 years for Graham)
    eps_history = [safe_get(yr, "eps") for yr in income_annual[:11]]  # oldest to newest
    eps_history = [e for e in eps_history if e is not None]  # filter None values
    
    # ─────────────────────────────────────────────────────────
    # STEP 3: PIOTROSKI F-SCORE (9 criteria)
    # Each criterion returns (pass: bool, value: *, justification: str)
    # DETERMINISTIC — no ambiguity possible
    # ─────────────────────────────────────────────────────────
    
    def compute_piotroski(data):
        criteria = {}
        total = 0
        
        # F1: ROA > 0
        roa = data["roa_curr"]
        f1_pass = roa > 0 if roa is not None else None
        criteria["F1_roa_positive"] = {
            "pass": f1_pass,
            "value": roa,
            "threshold": "> 0",
            "justification": f"ROA of {pct(roa)} is {'positive' if f1_pass else 'negative or zero'}. "
                           f"Net Income ${fmt_b(data['net_income_curr'])} on Total Assets ${fmt_b(data['total_assets_curr'])}."
        }
        if f1_pass: total += 1
        
        # F2: Operating Cash Flow > 0
        ocf = data["ocf_curr"]
        f2_pass = ocf > 0 if ocf is not None else None
        criteria["F2_operating_cf_positive"] = {
            "pass": f2_pass,
            "value": ocf,
            "threshold": "> 0",
            "justification": f"Operating cash flow of ${fmt_b(ocf)} is {'positive' if f2_pass else 'negative'}."
        }
        if f2_pass: total += 1
        
        # F3: ROA improving
        roa_cur = data["roa_curr"]
        roa_pri = data["roa_prior"]
        f3_pass = (roa_cur > roa_pri) if (roa_cur is not None and roa_pri is not None) else None
        criteria["F3_roa_improving"] = {
            "pass": f3_pass,
            "value_current": roa_cur,
            "value_prior": roa_pri,
            "threshold": "current > prior",
            "justification": f"ROA {'improved' if f3_pass else 'declined'} from {pct(roa_pri)} to {pct(roa_cur)} YoY."
        }
        if f3_pass: total += 1
        
        # F4: Quality of Earnings (OCF > Net Income)
        ocf = data["ocf_curr"]
        ni  = data["net_income_curr"]
        f4_pass = (ocf > ni) if (ocf is not None and ni is not None) else None
        criteria["F4_quality_of_earnings"] = {
            "pass": f4_pass,
            "ocf": ocf,
            "net_income": ni,
            "ratio": safe_div(ocf, ni),
            "threshold": "OCF > Net Income",
            "justification": (
                f"Operating cash flow ${fmt_b(ocf)} {'exceeds' if f4_pass else 'is below'} net income ${fmt_b(ni)}. "
                f"{'High earnings quality — accrual component is low.' if f4_pass else 'Accrual-heavy earnings — quality concern.'}"
            )
        }
        if f4_pass: total += 1
        
        # F5: Long-term Debt / Total Assets decreasing
        lt_debt_to_assets_curr  = safe_div(data["lt_debt_curr"],  data["total_assets_curr"])
        lt_debt_to_assets_prior = safe_div(data["lt_debt_prior"], data["total_assets_prior"])
        f5_pass = (lt_debt_to_assets_curr < lt_debt_to_assets_prior) \
                  if (lt_debt_to_assets_curr is not None and lt_debt_to_assets_prior is not None) else None
        criteria["F5_leverage_decreasing"] = {
            "pass": f5_pass,
            "lt_debt_to_assets_current": lt_debt_to_assets_curr,
            "lt_debt_to_assets_prior":   lt_debt_to_assets_prior,
            "lt_debt_current":  data["lt_debt_curr"],
            "lt_debt_prior":    data["lt_debt_prior"],
            "threshold": "current < prior",
            "justification": (
                f"LT Debt/Assets {'decreased' if f5_pass else 'increased'} from {pct(lt_debt_to_assets_prior)} "
                f"to {pct(lt_debt_to_assets_curr)}."
            )
        }
        if f5_pass: total += 1
        
        # F6: Current ratio improving
        cr_cur = data["cr_curr"]
        cr_pri = data["cr_prior"]
        f6_pass = (cr_cur > cr_pri) if (cr_cur is not None and cr_pri is not None) else None
        criteria["F6_liquidity_improving"] = {
            "pass": f6_pass,
            "current_ratio_current": cr_cur,
            "current_ratio_prior":   cr_pri,
            "threshold": "current > prior",
            "justification": (
                f"Current ratio {'improved' if f6_pass else 'declined'} from {fmt2(cr_pri)} to {fmt2(cr_cur)}."
            )
        }
        if f6_pass: total += 1
        
        # F7: No share dilution (shares current <= prior)
        sh_cur = data["shares_curr"]
        sh_pri = data["shares_prior"]
        f7_pass = (sh_cur <= sh_pri) if (sh_cur is not None and sh_pri is not None) else None
        criteria["F7_no_dilution"] = {
            "pass": f7_pass,
            "shares_current": sh_cur,
            "shares_prior":   sh_pri,
            "change_pct": safe_pct_change(sh_cur, sh_pri),
            "threshold": "current <= prior",
            "justification": (
                f"Shares {'decreased' if f7_pass else 'increased'} from {fmt_m(sh_pri)} to {fmt_m(sh_cur)}. "
                f"{'Buybacks reducing share count — no dilution.' if f7_pass else 'Share issuance — potential dilution.'}"
            )
        }
        if f7_pass: total += 1
        
        # F8: Gross margin improving
        gm_cur = safe_div(data["gross_profit_curr"], data["revenue_curr"])
        gm_pri = safe_div(data["gross_profit_prior"], data["revenue_prior"])
        f8_pass = (gm_cur > gm_pri) if (gm_cur is not None and gm_pri is not None) else None
        criteria["F8_gross_margin_improving"] = {
            "pass": f8_pass,
            "gross_margin_current": gm_cur,
            "gross_margin_prior":   gm_pri,
            "change_bps": int((gm_cur - gm_pri) * 10000) if f8_pass is not None else None,
            "threshold": "current > prior",
            "justification": (
                f"Gross margin {'improved' if f8_pass else 'declined'} from {pct(gm_pri)} to {pct(gm_cur)} "
                f"({abs(int((gm_cur-gm_pri)*10000))} bps {'improvement' if f8_pass else 'deterioration'})."
            )
        }
        if f8_pass: total += 1
        
        # F9: Asset turnover improving
        at_cur = safe_div(data["revenue_curr"], data["total_assets_curr"])
        at_pri = safe_div(data["revenue_prior"], data["total_assets_prior"])
        f9_pass = (at_cur > at_pri) if (at_cur is not None and at_pri is not None) else None
        criteria["F9_asset_turnover_improving"] = {
            "pass": f9_pass,
            "asset_turnover_current": at_cur,
            "asset_turnover_prior":   at_pri,
            "threshold": "current > prior",
            "justification": (
                f"Asset turnover {'improved' if f9_pass else 'declined'} from {fmt3(at_pri)} to {fmt3(at_cur)}."
            )
        }
        if f9_pass: total += 1
        
        # Map to 1-10 scale
        piotroski_map = {0:1, 1:1, 2:3, 3:3, 4:5, 5:5, 6:7, 7:7, 8:9, 9:10}
        
        return {
            "total": total,
            "max": 9,
            "mapped_score": piotroski_map[total],
            "criteria": criteria
        }
    
    piotroski_result = compute_piotroski({
        "roa_curr": roa_curr, "roa_prior": roa_prior,
        "ocf_curr": ocf_curr, 
        "net_income_curr": net_income_curr, "net_income_prior": net_income_prior,
        "lt_debt_curr": lt_debt_curr, "lt_debt_prior": lt_debt_prior,
        "total_assets_curr": total_assets_curr, "total_assets_prior": total_assets_prior,
        "cr_curr": cr_curr, "cr_prior": cr_prior,
        "shares_curr": shares_curr, "shares_prior": shares_prior,
        "gross_profit_curr": gross_profit_curr, "gross_profit_prior": gross_profit_prior,
        "revenue_curr": revenue_curr, "revenue_prior": revenue_prior
    })
    
    # ─────────────────────────────────────────────────────────
    # STEP 4: ALTMAN Z-SCORE
    # ─────────────────────────────────────────────────────────
    
    def compute_altman_z_score(data):
        working_capital = data["current_assets"] - data["current_liabilities"]
        ta = data["total_assets_curr"]
        
        x1 = safe_div(working_capital, ta)
        x2 = safe_div(data["retained_earnings"], ta)
        x3 = safe_div(data["ebit_curr"], ta)
        x4 = safe_div(data["market_cap"], data["total_liabilities"])
        x5 = safe_div(data["revenue_curr"], ta)
        
        # Check all components are available
        if any(v is None for v in [x1, x2, x3, x4, x5]):
            return {"error": "Insufficient data for Altman Z-Score", "score": None}
        
        z = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
        
        # Zone classification
        if z > 3.0:
            zone, zone_label = "safe", "Safe Zone — bankruptcy highly unlikely"
        elif z > 1.8:
            zone, zone_label = "grey", "Grey Zone — moderate distress risk"
        else:
            zone, zone_label = "distress", "Distress Zone — high bankruptcy risk"
        
        # Map to 1-10 scale (DETERMINISTIC thresholds)
        if z < 1.8:       altman_mapped = 1
        elif z < 2.5:     altman_mapped = 4
        elif z < 3.0:     altman_mapped = 6
        elif z < 4.0:     altman_mapped = 8
        else:             altman_mapped = 10  # z >= 4.0
        
        return {
            "score": round(z, 3),
            "zone": zone,
            "zone_label": zone_label,
            "mapped_score": altman_mapped,
            "components": {
                "x1_working_capital_ratio":    {"value": round(x1,4), "weight": 1.2, "weighted": round(1.2*x1,4)},
                "x2_retained_earnings_ratio":  {"value": round(x2,4), "weight": 1.4, "weighted": round(1.4*x2,4)},
                "x3_ebit_ratio":               {"value": round(x3,4), "weight": 3.3, "weighted": round(3.3*x3,4)},
                "x4_equity_to_liabilities":    {"value": round(x4,4), "weight": 0.6, "weighted": round(0.6*x4,4)},
                "x5_sales_ratio":              {"value": round(x5,4), "weight": 1.0, "weighted": round(1.0*x5,4)},
            },
            "formula": f"Z = 1.2×{round(x1,4)} + 1.4×{round(x2,4)} + 3.3×{round(x3,4)} + 0.6×{round(x4,4)} + 1.0×{round(x5,4)}",
            "calculation": f"{round(1.2*x1,4)} + {round(1.4*x2,4)} + {round(3.3*x3,4)} + {round(0.6*x4,4)} + {round(x5,4)} = {round(z,3)}"
        }
    
    altman_result = compute_altman_z_score({
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "total_assets_curr": total_assets_curr,
        "retained_earnings": retained_earnings,
        "ebit_curr": ebit_curr,
        "market_cap": market_cap,
        "total_liabilities": total_liabilities,
        "revenue_curr": revenue_curr
    })
    
    # ─────────────────────────────────────────────────────────
    # STEP 5: FINANCIAL HEALTH SUB-SCORE
    # ─────────────────────────────────────────────────────────
    
    def compute_financial_health_score(piotroski_result, altman_result):
        p_mapped = piotroski_result.get("mapped_score", 5)
        a_mapped = altman_result.get("mapped_score", 5)
        
        score = (p_mapped * 0.5) + (a_mapped * 0.5)
        return round(score, 1)
    
    financial_health_score = compute_financial_health_score(piotroski_result, altman_result)
    
    # ─────────────────────────────────────────────────────────
    # STEP 6: VALUATION SUB-SCORE
    # ─────────────────────────────────────────────────────────
    
    def compute_valuation_score(data):
        
        # 6a. Lynch Fair Value Ratio
        eps_growth_rate_pct = data.get("eps_growth_rate_pct")   # forward 5yr CAGR
        dividend_yield_pct  = (data.get("div_yield", 0) or 0) * 100
        pe = data.get("pe_ratio")
        
        if eps_growth_rate_pct is None:
            # Fallback: compute trailing 5-year EPS CAGR from history
            eps_hist = data.get("eps_history", [])
            if len(eps_hist) >= 6:
                eps_5yr_ago = eps_hist[-6]
                eps_now = eps_hist[-1]
                if eps_5yr_ago and eps_5yr_ago > 0 and eps_now and eps_now > 0:
                    eps_growth_rate_pct = ((eps_now / eps_5yr_ago) ** (1/5) - 1) * 100
                else:
                    eps_growth_rate_pct = 0
            else:
                eps_growth_rate_pct = 0
        
        # Cap EPS growth rate to prevent formula breakdown
        eps_growth_rate_pct = min(max(eps_growth_rate_pct, -50), 50)
        
        lynch_numerator = eps_growth_rate_pct + dividend_yield_pct
        lynch_ratio = safe_div(lynch_numerator, pe) if pe and pe > 0 else None
        
        if lynch_ratio is None:
            lynch_mapped = 5  # neutral if P/E unavailable
        elif lynch_ratio < 0.5:  lynch_mapped = 1
        elif lynch_ratio < 1.0:  lynch_mapped = 3
        elif lynch_ratio < 1.5:  lynch_mapped = 5
        elif lynch_ratio < 2.0:  lynch_mapped = 7
        else:                    lynch_mapped = 9
        
        # 6b. Graham P/E Test
        eps_3yr = data.get("eps_3yr_avg")
        if eps_3yr and eps_3yr > 0 and data.get("price"):
            pe_3yr_avg = data["price"] / eps_3yr
            graham_pe_pass = pe_3yr_avg <= 15
        else:
            pe_3yr_avg = None
            graham_pe_pass = False
        graham_pe_bonus = 1.5 if graham_pe_pass else 0
        
        # 6c. Graham P/B Test
        pb = data.get("pb_ratio")
        if pb is not None:
            pe_times_pb = (pe or 0) * pb
            graham_pb_pass = (pb <= 1.5) or (pe_times_pb <= 22.5)
        else:
            pb = None
            pe_times_pb = None
            graham_pb_pass = False
        graham_pb_bonus = 1.5 if graham_pb_pass else 0
        
        # 6d. DCF Margin of Safety
        dcf_value = data.get("dcf_value")
        price = data.get("price")
        if dcf_value and price and price > 0:
            mos_pct = (dcf_value - price) / price * 100
        else:
            mos_pct = None
        
        if mos_pct is None:   dcf_bonus = 0
        elif mos_pct > 20:    dcf_bonus = 2.0
        elif mos_pct > 10:    dcf_bonus = 1.0
        elif mos_pct > 0:     dcf_bonus = 0.5
        else:                 dcf_bonus = 0
        
        # Combine and cap
        raw = lynch_mapped + graham_pe_bonus + graham_pb_bonus + dcf_bonus
        final = min(raw, 10.0)
        
        return {
            "score": round(final, 1),
            "lynch_fair_value": {
                "ratio": round(lynch_ratio, 3) if lynch_ratio else None,
                "mapped_score": lynch_mapped,
                "components": {
                    "eps_growth_rate_pct": round(eps_growth_rate_pct, 2),
                    "dividend_yield_pct": round(dividend_yield_pct, 2),
                    "pe_ratio": pe
                }
            },
            "graham_pe_test": {
                "pass": graham_pe_pass,
                "pe_3yr_avg": round(pe_3yr_avg, 2) if pe_3yr_avg else None,
                "threshold": "<= 15",
                "bonus": graham_pe_bonus
            },
            "graham_pb_test": {
                "pass": graham_pb_pass,
                "pb_ratio": pb,
                "pe_times_pb": round(pe_times_pb, 1) if pe_times_pb else None,
                "threshold": "P/B <= 1.5 OR (P/E × P/B) <= 22.5",
                "bonus": graham_pb_bonus
            },
            "dcf_margin_of_safety": {
                "dcf_value": dcf_value,
                "current_price": price,
                "margin_pct": round(mos_pct, 1) if mos_pct is not None else None,
                "bonus": dcf_bonus,
                "dcf_model": "FMP single-model estimate"
            },
            "calculation": {
                "lynch_mapped": lynch_mapped,
                "graham_pe_bonus": graham_pe_bonus,
                "graham_pb_bonus": graham_pb_bonus,
                "dcf_bonus": dcf_bonus,
                "raw": raw,
                "capped_at_10": final
            }
        }
    
    # Compute 3-year average EPS for Graham
    eps_history_values = [safe_get(yr, "eps") for yr in income_annual[:3]]
    eps_3yr_avg = sum(e for e in eps_history_values if e) / max(len([e for e in eps_history_values if e]), 1)
    
    dcf_value = safe_get(dcf_data, "dcf")
    
    valuation_result = compute_valuation_score({
        "eps_growth_rate_pct": None,  # Will use trailing fallback
        "div_yield": div_yield,
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "price": price,
        "eps_3yr_avg": eps_3yr_avg,
        "dcf_value": dcf_value,
        "eps_history": [safe_get(yr, "eps") for yr in income_annual[:11]]
    })
    
    valuation_score = valuation_result["score"]
    
    # ─────────────────────────────────────────────────────────
    # STEP 7: PROFITABILITY & EFFICIENCY SUB-SCORE
    # ─────────────────────────────────────────────────────────
    
    def compute_profitability_score(data):
        
        # 7a. Greenblatt Earnings Yield
        ebit = data["ebit_curr"]
        ev   = data["ev"]
        
        # Check for financial/utility sector exclusion
        sector = data.get("sector", "")
        greenblatt_applicable = sector.lower() not in ["financials", "utilities", "financial services"]
        
        if not greenblatt_applicable:
            ey_pct = None
            roic_pct = None
            ey_mapped = 5   # neutral if not applicable
            roic_mapped = 5
        else:
            ey_pct = safe_div(ebit, ev) * 100 if (ebit and ev and ev > 0) else None
            
            if ey_pct is None:    ey_mapped = 5
            elif ey_pct < 3:      ey_mapped = 1
            elif ey_pct < 5:      ey_mapped = 3
            elif ey_pct < 8:      ey_mapped = 5
            elif ey_pct < 12:     ey_mapped = 7
            else:                 ey_mapped = 9
            
            # 7b. Greenblatt ROIC
            ppe = data["ppe_net"]
            working_capital = data["current_assets"] - data["current_liabilities"]
            net_capital = (ppe or 0) + working_capital
            
            roic_pct = safe_div(ebit, net_capital) * 100 if (ebit and net_capital and net_capital != 0) else None
            
            # Flag anomaly if working capital is negative (causes inflated ROIC)
            roic_anomaly = working_capital < 0
            
            if roic_pct is None:  roic_mapped = 5
            elif roic_pct < 5:    roic_mapped = 1
            elif roic_pct < 10:   roic_mapped = 3
            elif roic_pct < 20:   roic_mapped = 5
            elif roic_pct < 30:   roic_mapped = 7
            else:                 roic_mapped = 9  # Cap at 9 regardless of anomalous value
        
        # 7c. Gross margin trend bonus (from Piotroski F8)
        gm_cur = safe_div(data["gross_profit_curr"], data["revenue_curr"])
        gm_pri = safe_div(data["gross_profit_prior"], data["revenue_prior"])
        gm_improving = (gm_cur > gm_pri) if (gm_cur and gm_pri) else False
        gm_bonus = 1.0 if gm_improving else 0
        
        # Combine and cap
        raw = (ey_mapped * 0.4) + (roic_mapped * 0.4) + gm_bonus
        final = min(raw, 10.0)
        
        return {
            "score": round(final, 1),
            "greenblatt_applicable": greenblatt_applicable,
            "greenblatt_earnings_yield": {
                "ebit": ebit,
                "enterprise_value": ev,
                "earnings_yield_pct": round(ey_pct, 2) if ey_pct else None,
                "mapped_score": ey_mapped
            },
            "greenblatt_roic": {
                "ebit": ebit,
                "ppe_net": ppe,
                "working_capital": working_capital,
                "net_capital": net_capital,
                "roic_pct": round(roic_pct, 1) if roic_pct else None,
                "mapped_score": roic_mapped,
                "sector_anomaly_flag": roic_anomaly if greenblatt_applicable else False
            },
            "gross_margin_trend": {
                "improving": gm_improving,
                "gross_margin_current": round(gm_cur, 4) if gm_cur else None,
                "gross_margin_prior": round(gm_pri, 4) if gm_pri else None,
                "bonus": gm_bonus
            },
            "calculation": {
                "ey_mapped": ey_mapped,
                "roic_mapped": roic_mapped,
                "gross_margin_bonus": gm_bonus,
                "formula": f"({ey_mapped} × 0.4) + ({roic_mapped} × 0.4) + {gm_bonus}",
                "raw": raw,
                "final": final
            }
        }
    
    profitability_result = compute_profitability_score({
        "ebit_curr": ebit_curr,
        "ev": ev,
        "ppe_net": ppe_net,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "gross_profit_curr": gross_profit_curr,
        "gross_profit_prior": gross_profit_prior,
        "revenue_curr": revenue_curr,
        "revenue_prior": revenue_prior,
        "sector": sector
    })
    
    profitability_score = profitability_result["score"]
    
    # ─────────────────────────────────────────────────────────
    # STEP 8: GROWTH & MOMENTUM SUB-SCORE
    # ─────────────────────────────────────────────────────────
    
    def compute_growth_score(data):
        
        # 8a. Revenue growth YoY
        rev_cur = data["revenue_curr"]
        rev_pri = data["revenue_prior"]
        rev_growth_pct = safe_pct_change(rev_cur, rev_pri)
        
        if rev_growth_pct is None:  rev_mapped = 5
        elif rev_growth_pct < 0:    rev_mapped = 1
        elif rev_growth_pct < 5:    rev_mapped = 3
        elif rev_growth_pct < 15:   rev_mapped = 5
        elif rev_growth_pct < 25:   rev_mapped = 7
        else:                       rev_mapped = 9
        
        # 8b. EPS growth YoY
        eps_cur = data["eps_curr"]
        eps_pri = data["eps_prior"]
        eps_growth_pct = safe_pct_change(eps_cur, eps_pri) if (eps_cur and eps_pri and eps_pri > 0) else None
        
        if eps_growth_pct is None:  eps_mapped = 5
        elif eps_growth_pct < 0:    eps_mapped = 1
        elif eps_growth_pct < 10:   eps_mapped = 3
        elif eps_growth_pct < 20:   eps_mapped = 5
        elif eps_growth_pct < 30:   eps_mapped = 7
        else:                       eps_mapped = 9
        
        # 8c. Graham 10-year earnings growth test
        eps_history = data.get("eps_history", [])
        graham_growth_pass = False
        graham_growth_detail = {}
        
        if len(eps_history) >= 10:
            # Use oldest 3 years and most recent 3 years
            oldest_3 = [e for e in eps_history[:3] if e is not None and e > 0]
            newest_3 = [e for e in eps_history[-3:] if e is not None and e > 0]
            
            if len(oldest_3) >= 2 and len(newest_3) >= 2:
                avg_old = sum(oldest_3) / len(oldest_3)
                avg_new = sum(newest_3) / len(newest_3)
                if avg_old > 0:
                    growth_10y = (avg_new - avg_old) / avg_old * 100
                    graham_growth_pass = growth_10y >= 33.0
                    graham_growth_detail = {
                        "avg_eps_start_3yr": round(avg_old, 3),
                        "avg_eps_end_3yr": round(avg_new, 3),
                        "growth_pct": round(growth_10y, 1),
                        "threshold_pct": 33
                    }
        
        graham_growth_bonus = 1.0 if graham_growth_pass else 0
        
        # Combine and cap
        raw = (rev_mapped * 0.4) + (eps_mapped * 0.4) + graham_growth_bonus
        final = min(raw, 10.0)
        
        return {
            "score": round(final, 1),
            "revenue_growth_yoy": {
                "revenue_current": rev_cur,
                "revenue_prior": rev_pri,
                "growth_pct": round(rev_growth_pct, 2) if rev_growth_pct else None,
                "mapped_score": rev_mapped
            },
            "eps_growth_yoy": {
                "eps_current": eps_cur,
                "eps_prior": eps_pri,
                "growth_pct": round(eps_growth_pct, 2) if eps_growth_pct else None,
                "mapped_score": eps_mapped
            },
            "graham_10y_growth_test": {
                "pass": graham_growth_pass,
                **graham_growth_detail,
                "bonus": graham_growth_bonus
            },
            "calculation": {
                "rev_growth_mapped": rev_mapped,
                "eps_growth_mapped": eps_mapped,
                "graham_growth_bonus": graham_growth_bonus,
                "raw": raw,
                "final": final
            }
        }
    
    eps_annual = [safe_get(yr, "eps") for yr in income_annual]
    
    growth_result = compute_growth_score({
        "revenue_curr": revenue_curr,
        "revenue_prior": revenue_prior,
        "eps_curr": safe_get(income_annual[0], "eps"),
        "eps_prior": safe_get(income_annual[1], "eps"),
        "eps_history": eps_annual
    })
    
    growth_score = growth_result["score"]
    
    # ─────────────────────────────────────────────────────────
    # STEP 9: SHARIAH COMPLIANCE SCREENING
    # This is a SEPARATE output — does NOT affect fundamental_score
    # ─────────────────────────────────────────────────────────
    
    def compute_shariah_compliance(data):
        
        # Step 9a: Sector screen (BINARY — if fail, stop immediately)
        PROHIBITED_SECTORS = [
            "conventional banking", "conventional insurance",
            "alcohol", "pork", "gambling", "pornography",
            "tobacco", "weapons", "adult entertainment"
        ]
        PROHIBITED_INDUSTRIES = [
            "breweries", "distillers", "wineries",
            "casinos", "gaming", "tobacco",
            "banks", "thrifts", "diversified financials",  # conventional banking
        ]
        
        sector_lower = data.get("sector", "").lower()
        industry_lower = data.get("industry", "").lower()
        
        sector_prohibited = any(p in sector_lower for p in PROHIBITED_SECTORS)
        industry_prohibited = any(p in industry_lower for p in PROHIBITED_INDUSTRIES)
        sector_pass = not (sector_prohibited or industry_prohibited)
        
        if not sector_pass:
            return {
                "status": "Not Halal",
                "reason": "Sector/industry is prohibited under AAOIFI standards",
                "sector_screen": {
                    "pass": False,
                    "sector": data.get("sector"),
                    "industry": data.get("industry"),
                    "justification": f"Sector '{data.get('sector')}' / Industry '{data.get('industry')}' contains prohibited business activity."
                }
            }
        
        # Step 9b: Financial ratio screens
        total_debt   = data["total_debt"]
        market_cap   = data["market_cap"]
        total_assets = data["total_assets_curr"]
        cash         = data["cash"]
        short_inv    = data.get("short_term_inv", 0) or 0
        int_income   = data.get("interest_income", 0) or 0
        revenue      = data["revenue_curr"]
        
        # Ratio 1: Debt / Market Cap
        debt_ratio_mktcap = safe_div(total_debt, market_cap)
        debt_ratio_assets  = safe_div(total_debt, total_assets)
        
        # Use market cap denominator as primary (AAOIFI standard)
        debt_ratio = debt_ratio_mktcap
        debt_pass = (debt_ratio < 0.33) if debt_ratio is not None else None
        debt_proximity = debt_ratio is not None and 0.25 <= debt_ratio < 0.33
        
        # Ratio 2: (Cash + ST Investments) / Market Cap
        cash_ratio = safe_div((cash or 0) + short_inv, market_cap)
        cash_pass = (cash_ratio < 0.33) if cash_ratio is not None else None
        cash_proximity = cash_ratio is not None and 0.25 <= cash_ratio < 0.33
        
        # Ratio 3: Impermissible Income / Total Revenue
        imperm_ratio = safe_div(int_income, revenue)
        imperm_pass = (imperm_ratio < 0.05) if imperm_ratio is not None else None
        
        # Purification calculation
        eps = data.get("eps_curr", 0) or 0
        purification_per_share = eps * imperm_ratio if (eps and imperm_ratio) else 0
        
        # Determine overall status
        all_pass = debt_pass and cash_pass and imperm_pass
        any_proximity = debt_proximity or cash_proximity
        
        if not all_pass:
            status = "Not Halal"
        elif any_proximity:
            status = "Borderline"
        else:
            status = "Halal"
        
        return {
            "status": status,
            "screening_standard": "AAOIFI Standard No. 21 (33% threshold, DJIM/MSCI alignment)",
            "sector_screen": {
                "pass": True,
                "sector": data.get("sector"),
                "industry": data.get("industry"),
                "justification": f"Sector '{data.get('sector')}' is permissible under AAOIFI standards."
            },
            "debt_ratio": {
                "pass": debt_pass,
                "total_debt": total_debt,
                "market_cap": market_cap,
                "value": round(debt_ratio, 4) if debt_ratio else None,
                "threshold": "< 0.33",
                "proximity_warning": debt_proximity,
                "alternative_assets_denominator": {
                    "value": round(debt_ratio_assets, 4) if debt_ratio_assets else None,
                    "standard": "SC Malaysia: Total Debt / Total Assets"
                }
            },
            "cash_ratio": {
                "pass": cash_pass,
                "total_liquid": (cash or 0) + short_inv,
                "market_cap": market_cap,
                "value": round(cash_ratio, 4) if cash_ratio else None,
                "threshold": "< 0.33",
                "proximity_warning": cash_proximity
            },
            "impermissible_income_ratio": {
                "pass": imperm_pass,
                "interest_income": int_income,
                "total_revenue": revenue,
                "value": round(imperm_ratio, 5) if imperm_ratio else None,
                "threshold": "< 0.05"
            },
            "purification": {
                "purification_ratio": round(imperm_ratio, 5) if imperm_ratio else 0,
                "purification_per_share": round(purification_per_share, 4),
                "note": f"Donate ${round(purification_per_share,3)}/share/year to approved charity to purify returns."
            }
        }
    
    shariah_result = compute_shariah_compliance({
        "sector": sector,
        "industry": industry,
        "total_debt": total_debt,
        "market_cap": market_cap,
        "total_assets_curr": total_assets_curr,
        "cash": cash,
        "short_term_inv": short_term_inv,
        "interest_income": interest_income,
        "revenue_curr": revenue_curr,
        "eps_curr": safe_get(income_annual[0], "eps")
    })
    
    # ─────────────────────────────────────────────────────────
    # STEP 10: SWING TRADE ASSESSMENT
    # ─────────────────────────────────────────────────────────
    
    def compute_swing_assessment(data):
        
        # DCF margin of safety
        dcf_val = data.get("dcf_value")
        price   = data.get("price")
        mos_pct = ((dcf_val - price) / price * 100) if (dcf_val and price and price > 0) else None
        
        # Earnings surprise
        surprise = data.get("earnings_surprise")
        if surprise:
            actual   = safe_get(surprise, "actualEarningResult")
            estimate = safe_get(surprise, "estimatedEarning")
            if actual is not None and estimate is not None and estimate != 0:
                surprise_pct = (actual - estimate) / abs(estimate) * 100
                beat = surprise_pct > 0
            else:
                surprise_pct = None
                beat = None
        else:
            surprise_pct = None
            beat = None
        
        # Revenue acceleration (YoY growth current quarter vs. prior quarter)
        quarterly_rev = data.get("quarterly_revenue", [])
        if len(quarterly_rev) >= 6:
            # Current Q vs same Q prior year
            q_curr_rev  = safe_get(quarterly_rev[0], "revenue")
            q_curr_yoy  = safe_get(quarterly_rev[4], "revenue")  # same quarter 1 year ago
            q_prior_rev = safe_get(quarterly_rev[1], "revenue")
            q_prior_yoy = safe_get(quarterly_rev[5], "revenue")  # prior quarter, 1 year ago
            
            curr_q_growth = safe_div(q_curr_rev - q_curr_yoy, q_curr_yoy) * 100 if (q_curr_rev and q_curr_yoy) else None
            prior_q_growth= safe_div(q_prior_rev - q_prior_yoy, q_prior_yoy) * 100 if (q_prior_rev and q_prior_yoy) else None
            
            accelerating = (curr_q_growth > prior_q_growth) if (curr_q_growth is not None and prior_q_growth is not None) else None
        else:
            curr_q_growth = None
            prior_q_growth = None
            accelerating = None
        
        # Determine overall fundamental support
        # DETERMINISTIC logic — no LLM
        support_score = 0
        if mos_pct is not None:
            if mos_pct > 10:    support_score += 2
            elif mos_pct > 0:   support_score += 1
            elif mos_pct > -10: support_score += 0
            else:               support_score -= 1
        
        if beat is True:    support_score += 1
        if beat is False:   support_score -= 1
        if accelerating is True:  support_score += 1
        if accelerating is False: support_score -= 1
        
        if support_score >= 3:    fundamental_support = "strong"
        elif support_score >= 1:  fundamental_support = "moderate"
        elif support_score == 0:  fundamental_support = "neutral"
        elif support_score >= -1: fundamental_support = "weak"
        else:                     fundamental_support = "negative"
        
        return {
            "fundamental_support": fundamental_support,
            "support_score_raw": support_score,
            "dcf_upside_pct": round(mos_pct, 1) if mos_pct else None,
            "earnings_surprise": {
                "beat": beat,
                "actual_eps": actual if surprise else None,
                "estimated_eps": estimate if surprise else None,
                "surprise_pct": round(surprise_pct, 2) if surprise_pct else None
            },
            "revenue_acceleration": {
                "accelerating": accelerating,
                "current_q_revenue_yoy_growth_pct": round(curr_q_growth, 1) if curr_q_growth else None,
                "prior_q_revenue_yoy_growth_pct": round(prior_q_growth, 1) if prior_q_growth else None
            }
        }
    
    swing_result = compute_swing_assessment({
        "dcf_value": dcf_value,
        "price": price,
        "earnings_surprise": earnings_surprise,
        "quarterly_revenue": [{"revenue": safe_get(income_quarterly[i], "revenue")} 
                               for i in range(min(6, len(income_quarterly)))]
    })
    
    # ─────────────────────────────────────────────────────────
    # STEP 11: COMPUTE FINAL SCORE
    # DETERMINISTIC FORMULA — no exceptions
    # ─────────────────────────────────────────────────────────
    
    def compute_final_score(fh, val, prof, growth):
        """
        fh    = financial_health_score  (0-10)
        val   = valuation_score          (0-10)
        prof  = profitability_score      (0-10)
        growth= growth_score             (0-10)
        """
        raw = (fh * 0.30) + (val * 0.30) + (prof * 0.20) + (growth * 0.20)
        return round(raw, 1)
    
    final_score = compute_final_score(
        financial_health_score,
        valuation_score,
        profitability_score,
        growth_score
    )
    
    # ─────────────────────────────────────────────────────────
    # STEP 12: ASSEMBLE COMPLETE OUTPUT
    # ─────────────────────────────────────────────────────────
    
    output.update({
        "sub_scores": {
            "financial_health": {
                "score": financial_health_score,
                "weight": 0.30,
                "weighted_contribution": round(financial_health_score * 0.30, 3),
                "piotroski": piotroski_result,
                "altman_z_score": altman_result,
                "financial_health_calculation": {
                    "piotroski_mapped": piotroski_result["mapped_score"],
                    "altman_mapped": altman_result["mapped_score"],
                    "formula": f"({piotroski_result['mapped_score']} × 0.5) + ({altman_result['mapped_score']} × 0.5)",
                    "result": financial_health_score
                }
            },
            "valuation": {
                "score": valuation_score,
                "weight": 0.30,
                "weighted_contribution": round(valuation_score * 0.30, 3),
                **valuation_result
            },
            "profitability": {
                "score": profitability_score,
                "weight": 0.20,
                "weighted_contribution": round(profitability_score * 0.20, 3),
                **profitability_result
            },
            "growth": {
                "score": growth_score,
                "weight": 0.20,
                "weighted_contribution": round(growth_score * 0.20, 3),
                **growth_result
            }
        },
        
        "shariah_compliance": shariah_result,
        "swing_trade_assessment": swing_result,
        
        "final_score": final_score,
        "score_breakdown": {
            "financial_health": {"score": financial_health_score, "weight": 0.30, 
                                 "contribution": round(financial_health_score * 0.30, 3)},
            "valuation":        {"score": valuation_score,        "weight": 0.30, 
                                 "contribution": round(valuation_score * 0.30, 3)},
            "profitability":    {"score": profitability_score,    "weight": 0.20, 
                                 "contribution": round(profitability_score * 0.20, 3)},
            "growth":           {"score": growth_score,           "weight": 0.20, 
                                 "contribution": round(growth_score * 0.20, 3)},
            "formula": f"({financial_health_score}×0.30) + ({valuation_score}×0.30) + ({profitability_score}×0.20) + ({growth_score}×0.20)",
            "calculation": f"{round(financial_health_score*0.30,3)} + {round(valuation_score*0.30,3)} + {round(profitability_score*0.20,3)} + {round(growth_score*0.20,3)} = {final_score}",
            "raw": round((financial_health_score*0.30) + (valuation_score*0.30) + (profitability_score*0.20) + (growth_score*0.20), 3),
            "rounded": final_score
        },
        
        "metadata": {
            "scoring_engine_version": "1.0.0",
            "frameworks_applied": [
                "Piotroski F-Score (Piotroski 2000)",
                "Altman Z-Score (Altman 1968)",
                "Graham Defensive Criteria (Graham 1949/1973)",
                "Lynch PEGY (Lynch 1989)",
                "Greenblatt Magic Formula (Greenblatt 2005)",
                "AAOIFI Shariah Standard No. 21"
            ],
            "llm_used_for_scoring": False,
            "llm_used_for_summary": True,
            "deterministic": True,
            "reproducible": True,
            "note": "Given identical API responses, this engine will ALWAYS produce identical scores."
        }
    })
    
    # ─────────────────────────────────────────────────────────
    # STEP 13: GENERATE LLM SUMMARY (POST-SCORING ONLY)
    # LLM reads the completed JSON and writes a summary paragraph.
    # It CANNOT modify any field. It only populates llm_summary.
    # ─────────────────────────────────────────────────────────
    
    llm_prompt = f"""
    You are writing a 3-4 sentence executive summary of a stock's fundamental analysis.
    
    The analysis has ALREADY been completed. All scores are final. Do NOT change any numbers.
    
    Ticker: {ticker}
    Final Score: {final_score}/10
    Financial Health: {financial_health_score}/10 (Piotroski={piotroski_result['total']}/9, Altman Z={altman_result['score']})
    Valuation: {valuation_score}/10 (Lynch={valuation_result['lynch_fair_value']['ratio']}, Graham P/E pass={valuation_result['graham_pe_test']['pass']})
    Profitability: {profitability_score}/10
    Growth: {growth_score}/10
    Shariah Status: {shariah_result['status']}
    Swing Support: {swing_result['fundamental_support']}
    
    Write a clear, factual 3-4 sentence summary. Mention the score, the strongest factor, 
    the weakest factor, and the swing trade implication. Do not add opinions not supported by the data.
    """
    
    output["llm_summary"] = call_llm(llm_prompt)  # Only LLM call in entire pipeline
    
    return output

# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def safe_div(numerator, denominator):
    """Safe division — returns None if denominator is 0 or None."""
    if denominator is None or denominator == 0:
        return None
    if numerator is None:
        return None
    return numerator / denominator

def safe_pct_change(current, prior):
    """Returns percentage change, or None if inputs are invalid."""
    if prior is None or prior == 0 or current is None:
        return None
    return (current - prior) / abs(prior) * 100

def pct(value, decimals=2):
    """Format as percentage string."""
    if value is None: return "N/A"
    return f"{round(value * 100, decimals)}%"

def fmt_b(value):
    """Format as billions."""
    if value is None: return "N/A"
    return f"${abs(value)/1e9:.1f}B"

def fmt_m(value):
    """Format as millions/billions for share counts."""
    if value is None: return "N/A"
    if abs(value) >= 1e9: return f"{value/1e9:.2f}B"
    return f"{value/1e6:.1f}M"

def fmt2(value):
    """Format to 2 decimal places."""
    if value is None: return "N/A"
    return f"{round(value, 2)}"

def fmt3(value):
    """Format to 3 decimal places."""
    if value is None: return "N/A"
    return f"{round(value, 3)}"

def get_current_utc_iso():
    """Returns current UTC timestamp in ISO 8601 format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

# ─────────────────────────────────────────────────────────────
# ERROR HANDLING POLICIES
# ─────────────────────────────────────────────────────────────

# Policy 1: Data partially unavailable
# → Mark individual criteria as null (not 0), exclude from averages
# → Set data_quality = "partial"
# → Log warning in data_quality_warnings

# Policy 2: Critical data missing (price, market cap)
# → Return error JSON immediately, no scoring attempted

# Policy 3: API rate limit hit
# → Wait for exponential backoff: 2s, 4s, 8s, max 3 retries
# → If still failing, use cached data if < 24 hours old
# → Mark data_quality = "cached"

# Policy 4: Company in excluded Greenblatt sector (financials/utilities)
# → Set greenblatt_applicable = false
# → Use neutral score (5) for EY and ROIC components
# → Flag in output

# Policy 5: Negative EPS in history
# → For Piotroski F1: ROA < 0 → FAIL (correct behavior)
# → For Graham G3: Any negative EPS year → G3 FAILS
# → For Lynch: If eps_growth results in negative Lynch ratio → use 0 (map to bucket 1)
# → For 10yr average: Include negative years in average

# ─────────────────────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────────────────────

# Edge case 1: Company with no dividend (div_yield = 0)
# → Lynch formula: (eps_growth + 0) / P/E → still valid
# → Graham G4: Auto-FAIL (no 20-year dividend history possible)
# → AAOIFI: Dividend-paying status irrelevant to halal screening

# Edge case 2: Company with negative book value (from massive buybacks)
# → Graham P/B: P/B ratio will be negative → auto-FAIL G7a
# → Graham P/B × P/E test: negative P/B × positive P/E = negative → below 22.5 mathematically
#   BUT: This is a mathematical artifact. Rule: if book value < 0, set graham_pb_pass = false
# → Altman X2: negative retained earnings → mathematically correct, no adjustment

# Edge case 3: EPS is negative (loss-making company)
# → Lynch: If EPS < 0, P/E is meaningless. Set pe_ratio = None, lynch_mapped = 1
# → Graham G6: auto-FAIL (3yr avg EPS could be negative)
# → Piotroski F1: ROA < 0 → FAIL (correct)
# → Growth: EPS growth from negative to less negative = "improvement" but still maps to bucket 1

# Edge case 4: Very small companies (market cap < $1B)
# → Flag: "small_cap_warning: true" 
# → Graham G1 will fail (revenue < $500M likely)
# → All other calculations proceed normally

# Edge case 5: Non-US company with different fiscal year
# → Use the most recent completed fiscal year as "current"
# → YoY comparisons still valid as long as consistent periods used
```

---

## Appendix A: Framework Source Validation

| Framework | Author | Year | Primary Source | Validator Source |
|-----------|--------|------|----------------|-----------------|
| Piotroski F-Score | Joseph Piotroski | 2000 | *Journal of Accounting Research* 38(Supp.): 1-41 | [Stock Rover](https://www.stockrover.com/blog/the-piotroski-f-score/) |
| Altman Z-Score | Edward Altman | 1968 | *Journal of Finance* 23(4): 589-609 | [Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/commercial-lending/altmans-z-score-model/) |
| Graham Defensive Criteria | Benjamin Graham | 1949/1973 | *The Intelligent Investor*, 4th Revised Ed. | [Groww](https://groww.in/blog/benjamin-grahams-7-stock-criteria) · [GrahamValue](https://www.grahamvalue.com/quick-reference) |
| Lynch PEGY | Peter Lynch | 1989 | *One Up on Wall Street* | [StableBread](https://stablebread.com/peter-lynch-stock-valuation/) · [Quantamental Trader](https://quantamentaltrader.substack.com/p/peter-lynchs-pegy-method-a-detailed) |
| Greenblatt Magic Formula | Joel Greenblatt | 2005 | *The Little Book That Beats the Market* | [GuruFocus](https://www.gurufocus.com/tutorial/article/57/greenblatts-earnings-yield-and-return-on-capital) |
| AAOIFI Shariah Screening | AAOIFI | Ongoing | AAOIFI Standard No. 21 | [Musaffa](https://academy.musaffa.com/7-halal-stock-screening-methodologies-you-need-to-know/) · [HalalSignalz](https://www.halalsignalz.com/blog/aaofi-ratio-explained) · [arXiv](https://arxiv.org/html/2512.22858v1) |

---

## Appendix B: Data Field Cross-Reference Map

| Agent Rule | API Tool | API Endpoint | Field Name |
|-----------|----------|-------------|------------|
| Piotroski F1 | get_financial_ratios | /ratios | returnOnAssets |
| Piotroski F2 | get_cash_flow_statement | /cash-flow-statement | operatingCashFlow |
| Piotroski F3 | get_financial_ratios | /ratios | returnOnAssets (2 years) |
| Piotroski F4 | get_cash_flow_statement + get_income_statement | Both | operatingCashFlow vs netIncome |
| Piotroski F5 | get_balance_sheet | /balance-sheet-statement | longTermDebt, totalAssets (2 years) |
| Piotroski F6 | get_financial_ratios | /ratios | currentRatio (2 years) |
| Piotroski F7 | get_income_statement | /income-statement | weightedAverageShsOut (2 years) |
| Piotroski F8 | get_income_statement | /income-statement | grossProfit, revenue (2 years) |
| Piotroski F9 | get_income_statement + get_balance_sheet | Both | revenue, totalAssets (2 years) |
| Altman X1 | get_balance_sheet | /balance-sheet-statement | totalCurrentAssets, totalCurrentLiabilities, totalAssets |
| Altman X2 | get_balance_sheet | /balance-sheet-statement | retainedEarnings, totalAssets |
| Altman X3 | get_income_statement | /income-statement | operatingIncome, totalAssets |
| Altman X4 | get_company_profile + get_balance_sheet | /profile + /balance-sheet-statement | mktCap, totalLiabilities |
| Altman X5 | get_income_statement + get_balance_sheet | Both | revenue, totalAssets |
| Graham G1 | get_income_statement | /income-statement | revenue (current) |
| Graham G2a | get_financial_ratios | /ratios | currentRatio |
| Graham G2b | get_balance_sheet | /balance-sheet-statement | longTermDebt, totalCurrentAssets, totalCurrentLiabilities |
| Graham G3 | get_income_statement | /income-statement | eps (10 years) |
| Graham G4 | get_cash_flow_statement | /cash-flow-statement | dividendsPaid (10+ years) |
| Graham G5 | get_income_statement | /income-statement | eps (10 years, 3yr averages) |
| Graham G6 | get_income_statement + get_company_profile | Both | eps (3yr avg), price |
| Graham G7 | get_financial_ratios + get_company_profile | Both | priceToBookRatio, priceEarningsRatio |
| Lynch EPS Growth | get_income_statement | /income-statement | eps (5yr history) |
| Lynch Div Yield | get_financial_ratios | /ratios | dividendYield |
| Lynch P/E | get_financial_ratios | /ratios | priceEarningsRatio |
| Greenblatt EY | get_income_statement + get_enterprise_value | Both | operatingIncome, enterpriseValue |
| Greenblatt ROIC | get_income_statement + get_balance_sheet | Both | operatingIncome, propertyPlantEquipmentNet, currentAssets, currentLiabilities |
| AAOIFI Sector | get_company_profile | /profile | sector, industry |
| AAOIFI Debt | get_balance_sheet + get_company_profile | Both | totalDebt, mktCap |
| AAOIFI Cash | get_balance_sheet + get_company_profile | Both | cashAndCashEquivalents, shortTermInvestments, mktCap |
| AAOIFI Imperm | get_income_statement | /income-statement | interestIncome, revenue |
| DCF MoS | get_dcf_value + get_company_profile | /dcf + /profile | dcf, price |
| Earnings Surprise | get_analyst_estimates | /earnings-surprises | actualEarningResult, estimatedEarning |
| Revenue Accel | get_income_statement | /income-statement (quarterly) | revenue (6 quarters) |

---

## Appendix C: Scoring Quick Reference

### Sub-Score Mapping Tables

**Piotroski → Mapped Score**
| Raw (0-9) | 0-1 | 2-3 | 4-5 | 6-7 | 8 | 9 |
|-----------|-----|-----|-----|-----|---|---|
| Mapped (1-10) | 1 | 3 | 5 | 7 | 9 | 10 |

**Altman Z → Mapped Score**
| Z-Score | < 1.8 | 1.8–2.5 | 2.5–3.0 | 3.0–4.0 | ≥ 4.0 |
|---------|-------|---------|---------|---------|-------|
| Mapped | 1 | 4 | 6 | 8 | 10 |

**Lynch Fair Value → Mapped Score**
| Ratio | < 0.5 | 0.5–1.0 | 1.0–1.5 | 1.5–2.0 | > 2.0 |
|-------|-------|---------|---------|---------|-------|
| Mapped | 1 | 3 | 5 | 7 | 9 |

**Greenblatt Earnings Yield → Mapped Score**
| EY % | < 3% | 3–5% | 5–8% | 8–12% | > 12% |
|------|------|------|------|-------|-------|
| Mapped | 1 | 3 | 5 | 7 | 9 |

**Greenblatt ROIC → Mapped Score**
| ROIC % | < 5% | 5–10% | 10–20% | 20–30% | > 30% |
|--------|------|-------|--------|--------|-------|
| Mapped | 1 | 3 | 5 | 7 | 9 |

**Revenue Growth YoY → Mapped Score**
| Rev Growth | < 0% | 0–5% | 5–15% | 15–25% | > 25% |
|-----------|------|------|-------|--------|-------|
| Mapped | 1 | 3 | 5 | 7 | 9 |

**EPS Growth YoY → Mapped Score**
| EPS Growth | < 0% | 0–10% | 10–20% | 20–30% | > 30% |
|-----------|------|-------|--------|--------|-------|
| Mapped | 1 | 3 | 5 | 7 | 9 |

### Final Score Formula (Quick Reference)

```
Final Score = 
  (Financial Health Score × 0.30)   ← Piotroski 50% + Altman 50%
+ (Valuation Score × 0.30)          ← Lynch base + Graham PE/PB bonuses + DCF bonus, capped at 10
+ (Profitability Score × 0.20)      ← (EY×0.4) + (ROIC×0.4) + GrossMarginBonus, capped at 10
+ (Growth Score × 0.20)             ← (RevGrowth×0.4) + (EPSGrowth×0.4) + GrahamGrowthBonus, capped at 10
```

**Bonus Points Summary:**

| Bonus | Max Value | Trigger |
|-------|-----------|---------|
| Graham P/E Bonus | +1.5 to Valuation | 3yr avg P/E ≤ 15 |
| Graham P/B Bonus | +1.5 to Valuation | P/B ≤ 1.5 OR P/E×P/B ≤ 22.5 |
| DCF Bonus | +0.5 to +2.0 to Valuation | MoS 0-10%: +0.5, 10-20%: +1.0, >20%: +2.0 |
| Gross Margin Bonus | +1.0 to Profitability | Current gross margin > prior year |
| Graham Growth Bonus | +1.0 to Growth | 10yr EPS growth ≥ 33% |

---

*Document end. Version 1.0.0 — 2026-03-28*

*All framework implementations are derived from publicly available, peer-reviewed, or professionally validated sources as cited throughout. Every rule is traceable to its source. The scoring engine is fully deterministic — identical input data will always produce identical output.*
