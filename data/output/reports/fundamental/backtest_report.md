# Fundamental Agent — 12-Month Sector Backtest Report

**Generated**: 2026-03-31 16:00:34
**Window**: March 2025 – February 2026 (12 months)
**Total Periods**: 600
**Total Trades (Directional)**: 156
**Abstentions (HOLD)**: 444

## 1. Performance Summary

| Metric | Value |
|--------|-------|
| Win Rate | 57.1% |
| Sharpe Ratio (annualized) | 0.53 |
| Max Drawdown | 66.54% |
| Profit Factor | 1.47 |
| Total Trades | 156 |
| BUY Signals | 132 |
| SELL Signals | 24 |
| HOLD Signals | 444 |
| Correct | 89 |
| Incorrect | 67 |

## 2. Sector Breakdown

| Sector | Trades | Win Rate | Sharpe | Max DD | Profit Factor | BUY | SELL | HOLD |
|--------|--------|----------|--------|--------|---------------|-----|------|------|
| Technology | 36 | 61.1% | 0.71 | 30.83% | 1.65 | 36 | 0 | 84 |
| Healthcare | 33 | 48.5% | 0.13 | 45.18% | 1.11 | 21 | 12 | 87 |
| Financials | 41 | 65.9% | 0.75 | 31.01% | 1.7 | 41 | 0 | 79 |
| Consumer_Staples | 0 | N/A | N/A | N/A% | N/A | 0 | 0 | 120 |
| Energy | 46 | 52.2% | 0.42 | 66.54% | 1.38 | 34 | 12 | 74 |

## 3. Confusion Matrix

3-class confusion matrix: predicted signal (rows) vs actual market direction (columns).

|              | Actual UP | Actual DOWN | Row Total |
|--------------|-----------|-------------|-----------|
| **Pred BUY**  | 80 (TP) | 52 (FP) | 132 |
| **Pred SELL** | 15 (FN) | 9 (TN) | 24 |
| **Pred HOLD** | 250 (Missed) | 194 (Avoided) | 444 |
| **Col Total** | 345 | 255 | 600 |

### Derived Classification Metrics

| Metric | Value |
|--------|-------|
| Accuracy (TP+TN)/(TP+FP+TN+FN) | 57.1% |
| Precision (TP/(TP+FP)) | 60.6% |
| Recall (TP/(TP+FN)) | 84.2% |
| Specificity (TN/(TN+FP)) | 14.8% |
| F1 Score | 70.5% |
| Abstention Rate | 74.0% |

### Per-Sector Confusion Matrices

#### Technology

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 22 | 14 |
| **Pred SELL** | 0 | 0 |
| **Pred HOLD** | 41 | 43 |

Directional Accuracy: 61.1% (22/36)

#### Healthcare

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 10 | 11 |
| **Pred SELL** | 6 | 6 |
| **Pred HOLD** | 51 | 36 |

Directional Accuracy: 48.5% (16/33)

#### Financials

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 27 | 14 |
| **Pred SELL** | 0 | 0 |
| **Pred HOLD** | 42 | 37 |

Directional Accuracy: 65.9% (27/41)

#### Consumer_Staples

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 0 | 0 |
| **Pred SELL** | 0 | 0 |
| **Pred HOLD** | 63 | 57 |

Directional Accuracy: N/A (0/0)

#### Energy

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 21 | 13 |
| **Pred SELL** | 9 | 3 |
| **Pred HOLD** | 53 | 21 |

Directional Accuracy: 52.2% (24/46)

## 4. Entry & Exit Signal Log

| # | Ticker | Sector | Month | Signal Date | Signal | Score | Actual Dir | Return % | Correct |
|---|--------|--------|-------|-------------|--------|-------|------------|----------|---------|
| 1 | AAPL | Technology | March 2025 | 2025-03-01 | HOLD | 44.9 | down | -9.9% | ➖ |
| 2 | ABBV | Healthcare | March 2025 | 2025-03-01 | SELL | 28.8 | down | -1.8% | ✅ |
| 3 | ABT | Healthcare | March 2025 | 2025-03-01 | HOLD | 54.1 | down | -5.2% | ➖ |
| 4 | AMZN | Technology | March 2025 | 2025-03-01 | HOLD | 48.9 | down | -9.2% | ➖ |
| 5 | ANET | Technology | March 2025 | 2025-03-01 | BUY | 69.8 | down | -16.2% | ❌ |
| 6 | AXP | Financials | March 2025 | 2025-03-01 | BUY | 67.5 | down | -11.8% | ❌ |
| 7 | BAC | Financials | March 2025 | 2025-03-01 | BUY | 67.9 | down | -10.0% | ❌ |
| 8 | BLK | Financials | March 2025 | 2025-03-01 | HOLD | 56.0 | down | -2.6% | ➖ |
| 9 | BMY | Healthcare | March 2025 | 2025-03-01 | HOLD | 48.8 | up | +0.7% | ➖ |
| 10 | C | Financials | March 2025 | 2025-03-01 | HOLD | 52.2 | down | -12.0% | ➖ |
| 11 | CI | Healthcare | March 2025 | 2025-03-01 | HOLD | 50.3 | up | +5.8% | ➖ |
| 12 | CL | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 59.2 | up | +1.8% | ➖ |
| 13 | COP | Energy | March 2025 | 2025-03-01 | HOLD | 53.2 | up | +3.2% | ➖ |
| 14 | COST | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 51.4 | down | -11.3% | ➖ |
| 15 | CRM | Technology | March 2025 | 2025-03-01 | HOLD | 52.7 | down | -9.4% | ➖ |
| 16 | CVS | Healthcare | March 2025 | 2025-03-01 | HOLD | 56.9 | up | +2.2% | ➖ |
| 17 | CVX | Energy | March 2025 | 2025-03-01 | HOLD | 43.8 | up | +4.7% | ➖ |
| 18 | EOG | Energy | March 2025 | 2025-03-01 | BUY | 66.1 | down | -0.3% | ❌ |
| 19 | GIS | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 49.1 | down | -2.5% | ➖ |
| 20 | GOOGL | Technology | March 2025 | 2025-03-01 | HOLD | 61.9 | down | -9.3% | ➖ |
| 21 | GS | Financials | March 2025 | 2025-03-01 | BUY | 63.6 | down | -12.7% | ❌ |
| 22 | HAL | Energy | March 2025 | 2025-03-01 | BUY | 68.1 | down | -4.3% | ❌ |
| 23 | JNJ | Healthcare | March 2025 | 2025-03-01 | HOLD | 49.2 | down | -0.8% | ➖ |
| 24 | JPM | Financials | March 2025 | 2025-03-01 | BUY | 68.0 | down | -8.2% | ❌ |
| 25 | KO | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 46.1 | down | -0.5% | ➖ |
| 26 | LLY | Healthcare | March 2025 | 2025-03-01 | HOLD | 56.7 | down | -10.7% | ➖ |
| 27 | MA | Financials | March 2025 | 2025-03-01 | HOLD | 45.3 | down | -6.2% | ➖ |
| 28 | MCD | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 49.4 | up | +0.2% | ➖ |
| 29 | META | Technology | March 2025 | 2025-03-01 | BUY | 64.2 | down | -13.6% | ❌ |
| 30 | MO | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 54.3 | up | +6.0% | ➖ |
| 31 | MPC | Energy | March 2025 | 2025-03-01 | HOLD | 43.0 | down | -4.0% | ➖ |
| 32 | MRK | Healthcare | March 2025 | 2025-03-01 | BUY | 63.0 | down | -2.4% | ❌ |
| 33 | MS | Financials | March 2025 | 2025-03-01 | HOLD | 59.8 | down | -13.4% | ➖ |
| 34 | MSFT | Technology | March 2025 | 2025-03-01 | HOLD | 54.6 | down | -4.6% | ➖ |
| 35 | NVDA | Technology | March 2025 | 2025-03-01 | BUY | 64.5 | down | -12.2% | ❌ |
| 36 | ORCL | Technology | March 2025 | 2025-03-01 | HOLD | 44.7 | down | -15.2% | ➖ |
| 37 | OXY | Energy | March 2025 | 2025-03-01 | HOLD | 44.7 | up | +0.5% | ➖ |
| 38 | PEP | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 53.7 | down | -1.9% | ➖ |
| 39 | PFE | Healthcare | March 2025 | 2025-03-01 | BUY | 63.8 | down | -4.6% | ❌ |
| 40 | PG | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 52.0 | down | -3.3% | ➖ |
| 41 | PM | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 45.5 | up | +0.8% | ➖ |
| 42 | PSX | Energy | March 2025 | 2025-03-01 | SELL | 34.1 | down | -6.1% | ✅ |
| 43 | SLB | Energy | March 2025 | 2025-03-01 | BUY | 64.9 | up | +0.5% | ✅ |
| 44 | TSLA | Technology | March 2025 | 2025-03-01 | HOLD | 46.5 | down | -10.1% | ➖ |
| 45 | UNH | Healthcare | March 2025 | 2025-03-01 | HOLD | 40.7 | up | +9.1% | ➖ |
| 46 | V | Financials | March 2025 | 2025-03-01 | HOLD | 53.4 | down | -5.5% | ➖ |
| 47 | VLO | Energy | March 2025 | 2025-03-01 | HOLD | 44.8 | up | +0.6% | ➖ |
| 48 | WFC | Financials | March 2025 | 2025-03-01 | BUY | 62.7 | down | -9.7% | ❌ |
| 49 | WMT | Consumer_Staples | March 2025 | 2025-03-01 | HOLD | 56.9 | down | -13.4% | ➖ |
| 50 | XOM | Energy | March 2025 | 2025-03-01 | HOLD | 50.9 | up | +5.8% | ➖ |
| 51 | AAPL | Technology | April 2025 | 2025-04-01 | HOLD | 44.9 | down | -4.9% | ➖ |
| 52 | ABBV | Healthcare | April 2025 | 2025-04-01 | SELL | 28.8 | down | -6.8% | ✅ |
| 53 | ABT | Healthcare | April 2025 | 2025-04-01 | HOLD | 54.0 | down | -1.2% | ➖ |
| 54 | AMZN | Technology | April 2025 | 2025-04-01 | HOLD | 51.1 | down | -1.5% | ➖ |
| 55 | ANET | Technology | April 2025 | 2025-04-01 | BUY | 69.8 | up | +4.2% | ✅ |
| 56 | AXP | Financials | April 2025 | 2025-04-01 | BUY | 67.5 | down | -0.4% | ❌ |
| 57 | BAC | Financials | April 2025 | 2025-04-01 | BUY | 67.9 | down | -4.2% | ❌ |
| 58 | BLK | Financials | April 2025 | 2025-04-01 | HOLD | 56.0 | down | -2.7% | ➖ |
| 59 | BMY | Healthcare | April 2025 | 2025-04-01 | HOLD | 48.9 | down | -18.4% | ➖ |
| 60 | C | Financials | April 2025 | 2025-04-01 | HOLD | 52.2 | down | -3.0% | ➖ |
| 61 | CI | Healthcare | April 2025 | 2025-04-01 | HOLD | 50.3 | up | +2.5% | ➖ |
| 62 | CL | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 59.2 | down | -0.9% | ➖ |
| 63 | COP | Energy | April 2025 | 2025-04-01 | HOLD | 48.4 | down | -12.5% | ➖ |
| 64 | COST | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 51.4 | up | +4.9% | ➖ |
| 65 | CRM | Technology | April 2025 | 2025-04-01 | HOLD | 51.0 | down | -0.1% | ➖ |
| 66 | CVS | Healthcare | April 2025 | 2025-04-01 | HOLD | 57.0 | down | -3.0% | ➖ |
| 67 | CVX | Energy | April 2025 | 2025-04-01 | HOLD | 43.8 | down | -16.7% | ➖ |
| 68 | EOG | Energy | April 2025 | 2025-04-01 | BUY | 66.1 | down | -11.1% | ❌ |
| 69 | GIS | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 51.6 | down | -5.1% | ➖ |
| 70 | GOOGL | Technology | April 2025 | 2025-04-01 | HOLD | 61.9 | up | +3.6% | ➖ |
| 71 | GS | Financials | April 2025 | 2025-04-01 | BUY | 68.6 | up | +0.5% | ✅ |
| 72 | HAL | Energy | April 2025 | 2025-04-01 | BUY | 68.0 | down | -19.2% | ❌ |
| 73 | JNJ | Healthcare | April 2025 | 2025-04-01 | HOLD | 49.2 | down | -6.0% | ➖ |
| 74 | JPM | Financials | April 2025 | 2025-04-01 | BUY | 68.0 | up | +0.3% | ✅ |
| 75 | KO | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 46.1 | up | +1.0% | ➖ |
| 76 | LLY | Healthcare | April 2025 | 2025-04-01 | HOLD | 56.7 | up | +7.2% | ➖ |
| 77 | MA | Financials | April 2025 | 2025-04-01 | HOLD | 45.3 | down | -1.4% | ➖ |
| 78 | MCD | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 49.4 | up | +0.7% | ➖ |
| 79 | META | Technology | April 2025 | 2025-04-01 | BUY | 64.2 | down | -3.8% | ❌ |
| 80 | MO | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 54.4 | down | -2.1% | ➖ |
| 81 | MPC | Energy | April 2025 | 2025-04-01 | HOLD | 43.0 | down | -5.1% | ➖ |
| 82 | MRK | Healthcare | April 2025 | 2025-04-01 | BUY | 63.0 | down | -5.6% | ❌ |
| 83 | MS | Financials | April 2025 | 2025-04-01 | HOLD | 59.8 | down | -0.4% | ➖ |
| 84 | MSFT | Technology | April 2025 | 2025-04-01 | HOLD | 54.6 | up | +5.0% | ➖ |
| 85 | NVDA | Technology | April 2025 | 2025-04-01 | BUY | 67.0 | up | +0.6% | ✅ |
| 86 | ORCL | Technology | April 2025 | 2025-04-01 | HOLD | 46.4 | up | +1.1% | ➖ |
| 87 | OXY | Energy | April 2025 | 2025-04-01 | HOLD | 44.7 | down | -18.2% | ➖ |
| 88 | PEP | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 53.7 | down | -10.4% | ➖ |
| 89 | PFE | Healthcare | April 2025 | 2025-04-01 | BUY | 63.7 | down | -6.1% | ❌ |
| 90 | PG | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 52.0 | down | -4.2% | ➖ |
| 91 | PM | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 45.5 | up | +7.3% | ➖ |
| 92 | PSX | Energy | April 2025 | 2025-04-01 | SELL | 34.1 | down | -14.2% | ✅ |
| 93 | SLB | Energy | April 2025 | 2025-04-01 | BUY | 64.9 | down | -18.4% | ❌ |
| 94 | TSLA | Technology | April 2025 | 2025-04-01 | HOLD | 46.5 | up | +12.7% | ➖ |
| 95 | UNH | Healthcare | April 2025 | 2025-04-01 | HOLD | 40.8 | down | -21.9% | ➖ |
| 96 | V | Financials | April 2025 | 2025-04-01 | HOLD | 53.4 | down | -2.5% | ➖ |
| 97 | VLO | Energy | April 2025 | 2025-04-01 | HOLD | 44.8 | down | -12.5% | ➖ |
| 98 | WFC | Financials | April 2025 | 2025-04-01 | BUY | 62.7 | down | -1.0% | ❌ |
| 99 | WMT | Consumer_Staples | April 2025 | 2025-04-01 | HOLD | 55.5 | up | +9.4% | ➖ |
| 100 | XOM | Energy | April 2025 | 2025-04-01 | HOLD | 48.5 | down | -8.9% | ➖ |
| 101 | AAPL | Technology | May 2025 | 2025-05-01 | HOLD | 44.9 | down | -5.4% | ➖ |
| 102 | ABBV | Healthcare | May 2025 | 2025-05-01 | SELL | 28.6 | down | -4.6% | ✅ |
| 103 | ABT | Healthcare | May 2025 | 2025-05-01 | HOLD | 54.0 | up | +2.2% | ➖ |
| 104 | AMZN | Technology | May 2025 | 2025-05-01 | HOLD | 51.0 | up | +11.2% | ➖ |
| 105 | ANET | Technology | May 2025 | 2025-05-01 | BUY | 69.8 | up | +5.3% | ✅ |
| 106 | AXP | Financials | May 2025 | 2025-05-01 | BUY | 67.5 | up | +10.4% | ✅ |
| 107 | BAC | Financials | May 2025 | 2025-05-01 | BUY | 67.9 | up | +10.7% | ✅ |
| 108 | BLK | Financials | May 2025 | 2025-05-01 | HOLD | 56.0 | up | +7.2% | ➖ |
| 109 | BMY | Healthcare | May 2025 | 2025-05-01 | HOLD | 53.5 | down | -3.8% | ➖ |
| 110 | C | Financials | May 2025 | 2025-05-01 | HOLD | 52.2 | up | +11.0% | ➖ |
| 111 | CI | Healthcare | May 2025 | 2025-05-01 | HOLD | 50.3 | down | -6.9% | ➖ |
| 112 | CL | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 59.2 | up | +0.8% | ➖ |
| 113 | COP | Energy | May 2025 | 2025-05-01 | HOLD | 52.9 | down | -3.4% | ➖ |
| 114 | COST | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 51.4 | up | +4.7% | ➖ |
| 115 | CRM | Technology | May 2025 | 2025-05-01 | HOLD | 51.0 | down | -1.2% | ➖ |
| 116 | CVS | Healthcare | May 2025 | 2025-05-01 | HOLD | 57.0 | down | -4.0% | ➖ |
| 117 | CVX | Energy | May 2025 | 2025-05-01 | HOLD | 46.1 | up | +1.7% | ➖ |
| 118 | EOG | Energy | May 2025 | 2025-05-01 | BUY | 70.9 | down | -1.6% | ❌ |
| 119 | GIS | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 51.5 | down | -4.4% | ➖ |
| 120 | GOOGL | Technology | May 2025 | 2025-05-01 | HOLD | 61.9 | up | +8.2% | ➖ |
| 121 | GS | Financials | May 2025 | 2025-05-01 | BUY | 68.6 | up | +10.2% | ✅ |
| 122 | HAL | Energy | May 2025 | 2025-05-01 | BUY | 67.9 | down | -1.2% | ❌ |
| 123 | JNJ | Healthcare | May 2025 | 2025-05-01 | HOLD | 49.2 | up | +0.1% | ➖ |
| 124 | JPM | Financials | May 2025 | 2025-05-01 | BUY | 68.0 | up | +7.9% | ✅ |
| 125 | KO | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 46.2 | down | -0.6% | ➖ |
| 126 | LLY | Healthcare | May 2025 | 2025-05-01 | HOLD | 56.7 | down | -17.8% | ➖ |
| 127 | MA | Financials | May 2025 | 2025-05-01 | HOLD | 45.3 | up | +6.8% | ➖ |
| 128 | MCD | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 49.4 | down | -1.8% | ➖ |
| 129 | META | Technology | May 2025 | 2025-05-01 | BUY | 64.2 | up | +17.9% | ✅ |
| 130 | MO | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 54.4 | up | +2.5% | ➖ |
| 131 | MPC | Energy | May 2025 | 2025-05-01 | HOLD | 42.9 | up | +17.6% | ➖ |
| 132 | MRK | Healthcare | May 2025 | 2025-05-01 | BUY | 62.9 | down | -9.8% | ❌ |
| 133 | MS | Financials | May 2025 | 2025-05-01 | HOLD | 59.8 | up | +10.9% | ➖ |
| 134 | MSFT | Technology | May 2025 | 2025-05-01 | HOLD | 54.6 | up | +16.7% | ➖ |
| 135 | NVDA | Technology | May 2025 | 2025-05-01 | BUY | 67.0 | up | +24.1% | ✅ |
| 136 | ORCL | Technology | May 2025 | 2025-05-01 | HOLD | 46.4 | up | +17.6% | ➖ |
| 137 | OXY | Energy | May 2025 | 2025-05-01 | HOLD | 44.7 | up | +3.5% | ➖ |
| 138 | PEP | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 53.6 | down | -3.0% | ➖ |
| 139 | PFE | Healthcare | May 2025 | 2025-05-01 | BUY | 68.7 | down | -1.9% | ❌ |
| 140 | PG | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 51.9 | up | +4.5% | ➖ |
| 141 | PM | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 45.6 | up | +5.4% | ➖ |
| 142 | PSX | Energy | May 2025 | 2025-05-01 | SELL | 37.0 | up | +10.1% | ❌ |
| 143 | SLB | Energy | May 2025 | 2025-05-01 | BUY | 64.4 | down | -0.6% | ❌ |
| 144 | TSLA | Technology | May 2025 | 2025-05-01 | HOLD | 46.5 | up | +22.8% | ➖ |
| 145 | UNH | Healthcare | May 2025 | 2025-05-01 | HOLD | 40.6 | down | -26.6% | ➖ |
| 146 | V | Financials | May 2025 | 2025-05-01 | HOLD | 53.4 | up | +5.9% | ➖ |
| 147 | VLO | Energy | May 2025 | 2025-05-01 | HOLD | 52.2 | up | +12.0% | ➖ |
| 148 | WFC | Financials | May 2025 | 2025-05-01 | BUY | 62.7 | up | +5.9% | ✅ |
| 149 | WMT | Consumer_Staples | May 2025 | 2025-05-01 | HOLD | 55.5 | up | +1.8% | ➖ |
| 150 | XOM | Energy | May 2025 | 2025-05-01 | HOLD | 55.9 | down | -2.3% | ➖ |
| 151 | AAPL | Technology | June 2025 | 2025-06-01 | HOLD | 44.9 | up | +0.1% | ➖ |
| 152 | ABBV | Healthcare | June 2025 | 2025-06-01 | SELL | 30.9 | down | -2.0% | ✅ |
| 153 | ABT | Healthcare | June 2025 | 2025-06-01 | HOLD | 54.0 | up | +0.6% | ➖ |
| 154 | AMZN | Technology | June 2025 | 2025-06-01 | HOLD | 51.3 | up | +8.9% | ➖ |
| 155 | ANET | Technology | June 2025 | 2025-06-01 | BUY | 69.8 | up | +14.7% | ✅ |
| 156 | AXP | Financials | June 2025 | 2025-06-01 | BUY | 67.5 | up | +7.9% | ✅ |
| 157 | BAC | Financials | June 2025 | 2025-06-01 | BUY | 67.9 | up | +7.4% | ✅ |
| 158 | BLK | Financials | June 2025 | 2025-06-01 | HOLD | 56.0 | up | +7.5% | ➖ |
| 159 | BMY | Healthcare | June 2025 | 2025-06-01 | HOLD | 51.0 | down | -4.0% | ➖ |
| 160 | C | Financials | June 2025 | 2025-06-01 | HOLD | 52.2 | up | +12.0% | ➖ |
| 161 | CI | Healthcare | June 2025 | 2025-06-01 | HOLD | 50.3 | up | +3.5% | ➖ |
| 162 | CL | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 59.2 | down | -4.5% | ➖ |
| 163 | COP | Energy | June 2025 | 2025-06-01 | HOLD | 52.8 | up | +5.7% | ➖ |
| 164 | COST | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 51.4 | down | -5.3% | ➖ |
| 165 | CRM | Technology | June 2025 | 2025-06-01 | HOLD | 51.0 | up | +3.2% | ➖ |
| 166 | CVS | Healthcare | June 2025 | 2025-06-01 | HOLD | 56.9 | up | +7.0% | ➖ |
| 167 | CVX | Energy | June 2025 | 2025-06-01 | HOLD | 46.2 | up | +5.2% | ➖ |
| 168 | EOG | Energy | June 2025 | 2025-06-01 | BUY | 70.9 | up | +11.3% | ✅ |
| 169 | GIS | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 51.4 | down | -6.9% | ➖ |
| 170 | GOOGL | Technology | June 2025 | 2025-06-01 | HOLD | 61.9 | up | +4.1% | ➖ |
| 171 | GS | Financials | June 2025 | 2025-06-01 | BUY | 63.6 | up | +15.1% | ✅ |
| 172 | HAL | Energy | June 2025 | 2025-06-01 | BUY | 67.9 | up | +5.9% | ✅ |
| 173 | JNJ | Healthcare | June 2025 | 2025-06-01 | HOLD | 49.2 | down | -1.8% | ➖ |
| 174 | JPM | Financials | June 2025 | 2025-06-01 | BUY | 68.0 | up | +8.8% | ✅ |
| 175 | KO | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 46.2 | down | -1.8% | ➖ |
| 176 | LLY | Healthcare | June 2025 | 2025-06-01 | HOLD | 56.7 | up | +5.1% | ➖ |
| 177 | MA | Financials | June 2025 | 2025-06-01 | HOLD | 45.3 | down | -6.0% | ➖ |
| 178 | MCD | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 49.4 | down | -6.6% | ➖ |
| 179 | META | Technology | June 2025 | 2025-06-01 | BUY | 64.2 | up | +13.4% | ✅ |
| 180 | MO | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 54.4 | down | -1.4% | ➖ |
| 181 | MPC | Energy | June 2025 | 2025-06-01 | HOLD | 43.0 | up | +4.2% | ➖ |
| 182 | MRK | Healthcare | June 2025 | 2025-06-01 | BUY | 62.8 | up | +4.0% | ✅ |
| 183 | MS | Financials | June 2025 | 2025-06-01 | HOLD | 59.8 | up | +9.9% | ➖ |
| 184 | MSFT | Technology | June 2025 | 2025-06-01 | HOLD | 54.6 | up | +7.7% | ➖ |
| 185 | NVDA | Technology | June 2025 | 2025-06-01 | BUY | 64.5 | up | +16.8% | ✅ |
| 186 | ORCL | Technology | June 2025 | 2025-06-01 | HOLD | 44.7 | up | +27.0% | ➖ |
| 187 | OXY | Energy | June 2025 | 2025-06-01 | HOLD | 44.7 | up | +5.0% | ➖ |
| 188 | PEP | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 53.6 | up | +0.8% | ➖ |
| 189 | PFE | Healthcare | June 2025 | 2025-06-01 | BUY | 68.6 | up | +3.0% | ✅ |
| 190 | PG | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 52.0 | down | -5.9% | ➖ |
| 191 | PM | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 45.7 | up | +1.0% | ➖ |
| 192 | PSX | Energy | June 2025 | 2025-06-01 | SELL | 37.0 | up | +5.1% | ❌ |
| 193 | SLB | Energy | June 2025 | 2025-06-01 | BUY | 69.4 | up | +3.8% | ✅ |
| 194 | TSLA | Technology | June 2025 | 2025-06-01 | HOLD | 46.5 | down | -6.6% | ➖ |
| 195 | UNH | Healthcare | June 2025 | 2025-06-01 | HOLD | 47.8 | up | +3.1% | ➖ |
| 196 | V | Financials | June 2025 | 2025-06-01 | HOLD | 49.4 | down | -4.5% | ➖ |
| 197 | VLO | Energy | June 2025 | 2025-06-01 | HOLD | 44.8 | up | +4.4% | ➖ |
| 198 | WFC | Financials | June 2025 | 2025-06-01 | BUY | 62.7 | up | +6.3% | ✅ |
| 199 | WMT | Consumer_Staples | June 2025 | 2025-06-01 | HOLD | 55.5 | down | -1.5% | ➖ |
| 200 | XOM | Energy | June 2025 | 2025-06-01 | HOLD | 55.9 | up | +6.9% | ➖ |
| 201 | AAPL | Technology | July 2025 | 2025-07-01 | HOLD | 44.9 | up | +1.9% | ➖ |
| 202 | ABBV | Healthcare | July 2025 | 2025-07-01 | SELL | 30.9 | up | +2.9% | ❌ |
| 203 | ABT | Healthcare | July 2025 | 2025-07-01 | HOLD | 54.1 | down | -5.1% | ➖ |
| 204 | AMZN | Technology | July 2025 | 2025-07-01 | HOLD | 49.0 | up | +4.9% | ➖ |
| 205 | ANET | Technology | July 2025 | 2025-07-01 | BUY | 66.8 | up | +19.3% | ✅ |
| 206 | AXP | Financials | July 2025 | 2025-07-01 | BUY | 67.5 | down | -4.6% | ❌ |
| 207 | BAC | Financials | July 2025 | 2025-07-01 | BUY | 67.9 | up | +1.4% | ✅ |
| 208 | BLK | Financials | July 2025 | 2025-07-01 | HOLD | 56.0 | up | +6.2% | ➖ |
| 209 | BMY | Healthcare | July 2025 | 2025-07-01 | HOLD | 51.0 | up | +0.6% | ➖ |
| 210 | C | Financials | July 2025 | 2025-07-01 | HOLD | 52.2 | up | +12.6% | ➖ |
| 211 | CI | Healthcare | July 2025 | 2025-07-01 | HOLD | 50.3 | down | -9.9% | ➖ |
| 212 | CL | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 59.2 | down | -5.0% | ➖ |
| 213 | COP | Energy | July 2025 | 2025-07-01 | HOLD | 53.0 | up | +7.7% | ➖ |
| 214 | COST | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 51.4 | down | -6.3% | ➖ |
| 215 | CRM | Technology | July 2025 | 2025-07-01 | HOLD | 51.0 | down | -2.9% | ➖ |
| 216 | CVS | Healthcare | July 2025 | 2025-07-01 | HOLD | 52.0 | down | -8.7% | ➖ |
| 217 | CVX | Energy | July 2025 | 2025-07-01 | HOLD | 43.7 | up | +7.2% | ➖ |
| 218 | EOG | Energy | July 2025 | 2025-07-01 | BUY | 66.0 | up | +2.2% | ✅ |
| 219 | GIS | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 51.3 | down | -3.9% | ➖ |
| 220 | GOOGL | Technology | July 2025 | 2025-07-01 | HOLD | 61.9 | up | +11.5% | ➖ |
| 221 | GS | Financials | July 2025 | 2025-07-01 | BUY | 63.6 | up | +3.2% | ✅ |
| 222 | HAL | Energy | July 2025 | 2025-07-01 | BUY | 67.9 | up | +9.9% | ✅ |
| 223 | JNJ | Healthcare | July 2025 | 2025-07-01 | HOLD | 49.2 | up | +9.5% | ➖ |
| 224 | JPM | Financials | July 2025 | 2025-07-01 | BUY | 68.0 | up | +3.9% | ✅ |
| 225 | KO | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 46.1 | down | -2.8% | ➖ |
| 226 | LLY | Healthcare | July 2025 | 2025-07-01 | HOLD | 56.7 | down | -2.5% | ➖ |
| 227 | MA | Financials | July 2025 | 2025-07-01 | HOLD | 45.3 | down | -0.4% | ➖ |
| 228 | MCD | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 49.3 | up | +3.9% | ➖ |
| 229 | META | Technology | July 2025 | 2025-07-01 | BUY | 64.2 | down | -5.8% | ❌ |
| 230 | MO | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 54.4 | up | +4.9% | ➖ |
| 231 | MPC | Energy | July 2025 | 2025-07-01 | HOLD | 43.0 | up | +2.8% | ➖ |
| 232 | MRK | Healthcare | July 2025 | 2025-07-01 | BUY | 62.9 | up | +3.3% | ✅ |
| 233 | MS | Financials | July 2025 | 2025-07-01 | HOLD | 59.8 | up | +2.9% | ➖ |
| 234 | MSFT | Technology | July 2025 | 2025-07-01 | HOLD | 52.1 | up | +3.2% | ➖ |
| 235 | NVDA | Technology | July 2025 | 2025-07-01 | BUY | 64.5 | up | +13.5% | ✅ |
| 236 | ORCL | Technology | July 2025 | 2025-07-01 | HOLD | 46.0 | up | +14.9% | ➖ |
| 237 | OXY | Energy | July 2025 | 2025-07-01 | HOLD | 44.7 | up | +5.7% | ➖ |
| 238 | PEP | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 53.6 | up | +8.2% | ➖ |
| 239 | PFE | Healthcare | July 2025 | 2025-07-01 | BUY | 68.7 | down | -0.1% | ❌ |
| 240 | PG | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 51.9 | down | -3.4% | ➖ |
| 241 | PM | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 45.7 | down | -11.0% | ➖ |
| 242 | PSX | Energy | July 2025 | 2025-07-01 | SELL | 34.0 | up | +4.3% | ❌ |
| 243 | SLB | Energy | July 2025 | 2025-07-01 | BUY | 64.5 | up | +1.1% | ✅ |
| 244 | TSLA | Technology | July 2025 | 2025-07-01 | HOLD | 46.5 | up | +0.4% | ➖ |
| 245 | UNH | Healthcare | July 2025 | 2025-07-01 | HOLD | 42.8 | down | -14.7% | ➖ |
| 246 | V | Financials | July 2025 | 2025-07-01 | HOLD | 53.4 | down | -1.2% | ➖ |
| 247 | VLO | Energy | July 2025 | 2025-07-01 | HOLD | 44.8 | up | +3.7% | ➖ |
| 248 | WFC | Financials | July 2025 | 2025-07-01 | BUY | 62.7 | up | +2.1% | ✅ |
| 249 | WMT | Consumer_Staples | July 2025 | 2025-07-01 | HOLD | 55.5 | down | -0.2% | ➖ |
| 250 | XOM | Energy | July 2025 | 2025-07-01 | HOLD | 50.9 | up | +3.8% | ➖ |
| 251 | AAPL | Technology | August 2025 | 2025-08-01 | HOLD | 44.9 | up | +12.0% | ➖ |
| 252 | ABBV | Healthcare | August 2025 | 2025-08-01 | SELL | 31.0 | up | +11.3% | ❌ |
| 253 | ABT | Healthcare | August 2025 | 2025-08-01 | HOLD | 56.4 | up | +5.1% | ➖ |
| 254 | AMZN | Technology | August 2025 | 2025-08-01 | HOLD | 49.0 | down | -2.2% | ➖ |
| 255 | ANET | Technology | August 2025 | 2025-08-01 | BUY | 66.8 | up | +10.8% | ✅ |
| 256 | AXP | Financials | August 2025 | 2025-08-01 | BUY | 67.5 | up | +10.7% | ✅ |
| 257 | BAC | Financials | August 2025 | 2025-08-01 | BUY | 67.9 | up | +7.3% | ✅ |
| 258 | BLK | Financials | August 2025 | 2025-08-01 | HOLD | 56.0 | up | +1.9% | ➖ |
| 259 | BMY | Healthcare | August 2025 | 2025-08-01 | HOLD | 51.0 | up | +8.9% | ➖ |
| 260 | C | Financials | August 2025 | 2025-08-01 | HOLD | 47.2 | up | +3.7% | ➖ |
| 261 | CI | Healthcare | August 2025 | 2025-08-01 | HOLD | 50.3 | up | +12.5% | ➖ |
| 262 | CL | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 59.2 | up | +0.3% | ➖ |
| 263 | COP | Energy | August 2025 | 2025-08-01 | HOLD | 53.1 | up | +4.7% | ➖ |
| 264 | COST | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 51.4 | up | +0.5% | ➖ |
| 265 | CRM | Technology | August 2025 | 2025-08-01 | HOLD | 53.4 | down | -0.8% | ➖ |
| 266 | CVS | Healthcare | August 2025 | 2025-08-01 | HOLD | 56.9 | up | +17.8% | ➖ |
| 267 | CVX | Energy | August 2025 | 2025-08-01 | HOLD | 43.8 | up | +7.1% | ➖ |
| 268 | EOG | Energy | August 2025 | 2025-08-01 | BUY | 66.1 | up | +4.0% | ✅ |
| 269 | GIS | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 46.8 | up | +0.7% | ➖ |
| 270 | GOOGL | Technology | August 2025 | 2025-08-01 | HOLD | 59.4 | up | +10.9% | ➖ |
| 271 | GS | Financials | August 2025 | 2025-08-01 | BUY | 63.6 | up | +3.5% | ✅ |
| 272 | HAL | Energy | August 2025 | 2025-08-01 | BUY | 68.0 | up | +1.5% | ✅ |
| 273 | JNJ | Healthcare | August 2025 | 2025-08-01 | HOLD | 49.2 | up | +8.3% | ➖ |
| 274 | JPM | Financials | August 2025 | 2025-08-01 | BUY | 64.0 | up | +1.8% | ✅ |
| 275 | KO | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 46.1 | up | +1.6% | ➖ |
| 276 | LLY | Healthcare | August 2025 | 2025-08-01 | HOLD | 56.7 | down | -0.8% | ➖ |
| 277 | MA | Financials | August 2025 | 2025-08-01 | HOLD | 45.3 | up | +5.1% | ➖ |
| 278 | MCD | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 49.3 | up | +4.5% | ➖ |
| 279 | META | Technology | August 2025 | 2025-08-01 | BUY | 64.2 | down | -4.5% | ❌ |
| 280 | MO | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 54.4 | up | +8.5% | ➖ |
| 281 | MPC | Energy | August 2025 | 2025-08-01 | HOLD | 43.0 | up | +6.2% | ➖ |
| 282 | MRK | Healthcare | August 2025 | 2025-08-01 | BUY | 62.9 | up | +7.7% | ✅ |
| 283 | MS | Financials | August 2025 | 2025-08-01 | HOLD | 59.8 | up | +5.6% | ➖ |
| 284 | MSFT | Technology | August 2025 | 2025-08-01 | HOLD | 52.1 | down | -4.9% | ➖ |
| 285 | NVDA | Technology | August 2025 | 2025-08-01 | BUY | 64.5 | down | -2.1% | ❌ |
| 286 | ORCL | Technology | August 2025 | 2025-08-01 | HOLD | 43.5 | down | -10.9% | ➖ |
| 287 | OXY | Energy | August 2025 | 2025-08-01 | HOLD | 44.7 | up | +8.3% | ➖ |
| 288 | PEP | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 53.7 | up | +7.8% | ➖ |
| 289 | PFE | Healthcare | August 2025 | 2025-08-01 | BUY | 68.7 | up | +6.3% | ✅ |
| 290 | PG | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 54.3 | up | +4.4% | ➖ |
| 291 | PM | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 45.6 | up | +1.9% | ➖ |
| 292 | PSX | Energy | August 2025 | 2025-08-01 | SELL | 34.1 | up | +9.2% | ❌ |
| 293 | SLB | Energy | August 2025 | 2025-08-01 | BUY | 64.5 | up | +9.0% | ✅ |
| 294 | TSLA | Technology | August 2025 | 2025-08-01 | HOLD | 46.5 | up | +8.3% | ➖ |
| 295 | UNH | Healthcare | August 2025 | 2025-08-01 | HOLD | 47.4 | up | +24.2% | ➖ |
| 296 | V | Financials | August 2025 | 2025-08-01 | HOLD | 53.4 | up | +2.0% | ➖ |
| 297 | VLO | Energy | August 2025 | 2025-08-01 | HOLD | 44.8 | up | +10.7% | ➖ |
| 298 | WFC | Financials | August 2025 | 2025-08-01 | HOLD | 52.7 | up | +2.5% | ➖ |
| 299 | WMT | Consumer_Staples | August 2025 | 2025-08-01 | HOLD | 55.5 | down | -0.8% | ➖ |
| 300 | XOM | Energy | August 2025 | 2025-08-01 | HOLD | 50.9 | up | +3.3% | ➖ |
| 301 | AAPL | Technology | September 2025 | 2025-09-01 | HOLD | 44.9 | up | +9.6% | ➖ |
| 302 | ABBV | Healthcare | September 2025 | 2025-09-01 | SELL | 28.9 | up | +6.1% | ❌ |
| 303 | ABT | Healthcare | September 2025 | 2025-09-01 | HOLD | 54.0 | up | +0.3% | ➖ |
| 304 | AMZN | Technology | September 2025 | 2025-09-01 | HOLD | 49.0 | down | -3.0% | ➖ |
| 305 | ANET | Technology | September 2025 | 2025-09-01 | BUY | 66.8 | up | +5.0% | ✅ |
| 306 | AXP | Financials | September 2025 | 2025-09-01 | BUY | 67.5 | up | +3.3% | ✅ |
| 307 | BAC | Financials | September 2025 | 2025-09-01 | HOLD | 57.9 | up | +3.9% | ➖ |
| 308 | BLK | Financials | September 2025 | 2025-09-01 | HOLD | 52.0 | up | +4.8% | ➖ |
| 309 | BMY | Healthcare | September 2025 | 2025-09-01 | HOLD | 51.0 | down | -6.4% | ➖ |
| 310 | C | Financials | September 2025 | 2025-09-01 | HOLD | 47.2 | up | +6.8% | ➖ |
| 311 | CI | Healthcare | September 2025 | 2025-09-01 | HOLD | 50.3 | down | -4.2% | ➖ |
| 312 | CL | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 59.2 | down | -4.4% | ➖ |
| 313 | COP | Energy | September 2025 | 2025-09-01 | HOLD | 53.3 | down | -3.1% | ➖ |
| 314 | COST | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 51.4 | down | -2.8% | ➖ |
| 315 | CRM | Technology | September 2025 | 2025-09-01 | HOLD | 53.4 | down | -4.2% | ➖ |
| 316 | CVS | Healthcare | September 2025 | 2025-09-01 | HOLD | 52.0 | up | +3.3% | ➖ |
| 317 | CVX | Energy | September 2025 | 2025-09-01 | HOLD | 43.8 | down | -2.8% | ➖ |
| 318 | EOG | Energy | September 2025 | 2025-09-01 | BUY | 66.1 | down | -9.2% | ❌ |
| 319 | GIS | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 46.8 | up | +0.7% | ➖ |
| 320 | GOOGL | Technology | September 2025 | 2025-09-01 | HOLD | 59.4 | up | +14.7% | ➖ |
| 321 | GS | Financials | September 2025 | 2025-09-01 | HOLD | 59.6 | up | +7.9% | ➖ |
| 322 | HAL | Energy | September 2025 | 2025-09-01 | BUY | 68.0 | up | +10.8% | ✅ |
| 323 | JNJ | Healthcare | September 2025 | 2025-09-01 | HOLD | 46.7 | up | +2.5% | ➖ |
| 324 | JPM | Financials | September 2025 | 2025-09-01 | BUY | 64.0 | up | +4.7% | ✅ |
| 325 | KO | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 46.1 | down | -3.5% | ➖ |
| 326 | LLY | Healthcare | September 2025 | 2025-09-01 | HOLD | 56.7 | down | -0.8% | ➖ |
| 327 | MA | Financials | September 2025 | 2025-09-01 | HOLD | 45.3 | down | -4.6% | ➖ |
| 328 | MCD | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 49.4 | down | -2.8% | ➖ |
| 329 | META | Technology | September 2025 | 2025-09-01 | BUY | 64.2 | up | +0.7% | ✅ |
| 330 | MO | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 54.5 | down | -0.7% | ➖ |
| 331 | MPC | Energy | September 2025 | 2025-09-01 | HOLD | 43.0 | up | +9.3% | ➖ |
| 332 | MRK | Healthcare | September 2025 | 2025-09-01 | BUY | 62.9 | down | -5.7% | ❌ |
| 333 | MS | Financials | September 2025 | 2025-09-01 | HOLD | 59.8 | up | +7.1% | ➖ |
| 334 | MSFT | Technology | September 2025 | 2025-09-01 | HOLD | 54.4 | up | +1.6% | ➖ |
| 335 | NVDA | Technology | September 2025 | 2025-09-01 | BUY | 64.5 | up | +4.4% | ✅ |
| 336 | ORCL | Technology | September 2025 | 2025-09-01 | HOLD | 43.3 | up | +25.0% | ➖ |
| 337 | OXY | Energy | September 2025 | 2025-09-01 | HOLD | 44.7 | up | +1.6% | ➖ |
| 338 | PEP | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 53.7 | down | -4.8% | ➖ |
| 339 | PFE | Healthcare | September 2025 | 2025-09-01 | BUY | 63.8 | down | -3.7% | ❌ |
| 340 | PG | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 51.5 | down | -2.2% | ➖ |
| 341 | PM | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 45.6 | down | -2.5% | ➖ |
| 342 | PSX | Energy | September 2025 | 2025-09-01 | SELL | 34.1 | up | +3.0% | ❌ |
| 343 | SLB | Energy | September 2025 | 2025-09-01 | BUY | 64.7 | down | -3.9% | ❌ |
| 344 | TSLA | Technology | September 2025 | 2025-09-01 | HOLD | 46.5 | up | +32.8% | ➖ |
| 345 | UNH | Healthcare | September 2025 | 2025-09-01 | HOLD | 42.8 | up | +12.1% | ➖ |
| 346 | V | Financials | September 2025 | 2025-09-01 | HOLD | 53.4 | down | -3.3% | ➖ |
| 347 | VLO | Energy | September 2025 | 2025-09-01 | HOLD | 44.9 | up | +13.2% | ➖ |
| 348 | WFC | Financials | September 2025 | 2025-09-01 | HOLD | 52.7 | up | +3.0% | ➖ |
| 349 | WMT | Consumer_Staples | September 2025 | 2025-09-01 | HOLD | 55.5 | up | +6.3% | ➖ |
| 350 | XOM | Energy | September 2025 | 2025-09-01 | HOLD | 48.5 | down | -0.1% | ➖ |
| 351 | AAPL | Technology | October 2025 | 2025-10-01 | HOLD | 44.9 | up | +6.6% | ➖ |
| 352 | ABBV | Healthcare | October 2025 | 2025-10-01 | SELL | 29.4 | down | -0.7% | ✅ |
| 353 | ABT | Healthcare | October 2025 | 2025-10-01 | HOLD | 54.1 | down | -6.5% | ➖ |
| 354 | AMZN | Technology | October 2025 | 2025-10-01 | HOLD | 49.0 | up | +1.5% | ➖ |
| 355 | ANET | Technology | October 2025 | 2025-10-01 | BUY | 66.8 | up | +8.7% | ✅ |
| 356 | AXP | Financials | October 2025 | 2025-10-01 | BUY | 67.5 | up | +8.3% | ✅ |
| 357 | BAC | Financials | October 2025 | 2025-10-01 | HOLD | 57.9 | up | +2.8% | ➖ |
| 358 | BLK | Financials | October 2025 | 2025-10-01 | HOLD | 52.0 | down | -5.8% | ➖ |
| 359 | BMY | Healthcare | October 2025 | 2025-10-01 | HOLD | 51.0 | up | +2.5% | ➖ |
| 360 | C | Financials | October 2025 | 2025-10-01 | HOLD | 47.2 | down | -1.3% | ➖ |
| 361 | CI | Healthcare | October 2025 | 2025-10-01 | HOLD | 50.3 | down | -14.3% | ➖ |
| 362 | CL | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 59.2 | down | -3.6% | ➖ |
| 363 | COP | Energy | October 2025 | 2025-10-01 | HOLD | 53.1 | down | -6.8% | ➖ |
| 364 | COST | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 51.4 | down | -0.6% | ➖ |
| 365 | CRM | Technology | October 2025 | 2025-10-01 | HOLD | 53.2 | up | +8.3% | ➖ |
| 366 | CVS | Healthcare | October 2025 | 2025-10-01 | HOLD | 52.1 | up | +2.6% | ➖ |
| 367 | CVX | Energy | October 2025 | 2025-10-01 | HOLD | 43.8 | down | -1.1% | ➖ |
| 368 | EOG | Energy | October 2025 | 2025-10-01 | BUY | 71.0 | down | -5.0% | ❌ |
| 369 | GIS | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 46.9 | down | -5.5% | ➖ |
| 370 | GOOGL | Technology | October 2025 | 2025-10-01 | HOLD | 59.4 | up | +15.8% | ➖ |
| 371 | GS | Financials | October 2025 | 2025-10-01 | HOLD | 59.6 | down | -0.8% | ➖ |
| 372 | HAL | Energy | October 2025 | 2025-10-01 | BUY | 68.0 | up | +9.6% | ✅ |
| 373 | JNJ | Healthcare | October 2025 | 2025-10-01 | HOLD | 46.7 | up | +2.0% | ➖ |
| 374 | JPM | Financials | October 2025 | 2025-10-01 | BUY | 64.0 | down | -1.4% | ❌ |
| 375 | KO | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 46.1 | up | +4.0% | ➖ |
| 376 | LLY | Healthcare | October 2025 | 2025-10-01 | HOLD | 56.7 | up | +10.7% | ➖ |
| 377 | MA | Financials | October 2025 | 2025-10-01 | HOLD | 45.3 | down | -2.5% | ➖ |
| 378 | MCD | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 49.4 | down | -0.5% | ➖ |
| 379 | META | Technology | October 2025 | 2025-10-01 | BUY | 64.2 | down | -9.2% | ❌ |
| 380 | MO | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 54.5 | down | -13.5% | ➖ |
| 381 | MPC | Energy | October 2025 | 2025-10-01 | HOLD | 43.1 | up | +1.5% | ➖ |
| 382 | MRK | Healthcare | October 2025 | 2025-10-01 | BUY | 63.0 | up | +2.8% | ✅ |
| 383 | MS | Financials | October 2025 | 2025-10-01 | HOLD | 59.8 | up | +4.0% | ➖ |
| 384 | MSFT | Technology | October 2025 | 2025-10-01 | HOLD | 54.4 | up | +1.5% | ➖ |
| 385 | NVDA | Technology | October 2025 | 2025-10-01 | BUY | 64.5 | up | +8.7% | ✅ |
| 386 | ORCL | Technology | October 2025 | 2025-10-01 | HOLD | 43.7 | down | -8.5% | ➖ |
| 387 | OXY | Energy | October 2025 | 2025-10-01 | HOLD | 44.7 | down | -13.9% | ➖ |
| 388 | PEP | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 53.7 | up | +5.1% | ➖ |
| 389 | PFE | Healthcare | October 2025 | 2025-10-01 | BUY | 63.8 | down | -4.7% | ❌ |
| 390 | PG | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 51.5 | down | -2.0% | ➖ |
| 391 | PM | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 45.6 | down | -9.3% | ➖ |
| 392 | PSX | Energy | October 2025 | 2025-10-01 | SELL | 34.1 | up | +0.8% | ❌ |
| 393 | SLB | Energy | October 2025 | 2025-10-01 | BUY | 64.5 | up | +5.7% | ✅ |
| 394 | TSLA | Technology | October 2025 | 2025-10-01 | HOLD | 46.5 | down | -1.0% | ➖ |
| 395 | UNH | Healthcare | October 2025 | 2025-10-01 | HOLD | 43.0 | down | -0.2% | ➖ |
| 396 | V | Financials | October 2025 | 2025-10-01 | HOLD | 53.4 | up | +1.1% | ➖ |
| 397 | VLO | Energy | October 2025 | 2025-10-01 | HOLD | 44.9 | down | -0.1% | ➖ |
| 398 | WFC | Financials | October 2025 | 2025-10-01 | HOLD | 52.7 | up | +2.6% | ➖ |
| 399 | WMT | Consumer_Staples | October 2025 | 2025-10-01 | HOLD | 55.5 | down | -0.8% | ➖ |
| 400 | XOM | Energy | October 2025 | 2025-10-01 | HOLD | 48.5 | up | +1.7% | ➖ |
| 401 | AAPL | Technology | November 2025 | 2025-11-01 | HOLD | 42.4 | up | +3.2% | ➖ |
| 402 | ABBV | Healthcare | November 2025 | 2025-11-01 | SELL | 29.1 | up | +4.4% | ❌ |
| 403 | ABT | Healthcare | November 2025 | 2025-11-01 | HOLD | 56.4 | up | +4.3% | ➖ |
| 404 | AMZN | Technology | November 2025 | 2025-11-01 | HOLD | 49.0 | down | -4.5% | ➖ |
| 405 | ANET | Technology | November 2025 | 2025-11-01 | BUY | 66.8 | down | -17.1% | ❌ |
| 406 | AXP | Financials | November 2025 | 2025-11-01 | BUY | 67.5 | up | +1.3% | ✅ |
| 407 | BAC | Financials | November 2025 | 2025-11-01 | HOLD | 57.9 | up | +0.4% | ➖ |
| 408 | BLK | Financials | November 2025 | 2025-11-01 | HOLD | 56.0 | down | -3.3% | ➖ |
| 409 | BMY | Healthcare | November 2025 | 2025-11-01 | HOLD | 51.0 | up | +6.8% | ➖ |
| 410 | C | Financials | November 2025 | 2025-11-01 | HOLD | 47.2 | up | +3.0% | ➖ |
| 411 | CI | Healthcare | November 2025 | 2025-11-01 | HOLD | 55.3 | up | +13.4% | ➖ |
| 412 | CL | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 59.2 | up | +4.3% | ➖ |
| 413 | COP | Energy | November 2025 | 2025-11-01 | HOLD | 53.0 | up | +0.7% | ➖ |
| 414 | COST | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 47.6 | up | +0.2% | ➖ |
| 415 | CRM | Technology | November 2025 | 2025-11-01 | HOLD | 50.9 | down | -11.5% | ➖ |
| 416 | CVS | Healthcare | November 2025 | 2025-11-01 | HOLD | 52.1 | up | +2.8% | ➖ |
| 417 | CVX | Energy | November 2025 | 2025-11-01 | HOLD | 43.8 | down | -3.1% | ➖ |
| 418 | EOG | Energy | November 2025 | 2025-11-01 | BUY | 70.9 | up | +1.9% | ✅ |
| 419 | GIS | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 49.2 | up | +1.6% | ➖ |
| 420 | GOOGL | Technology | November 2025 | 2025-11-01 | HOLD | 59.4 | up | +13.9% | ➖ |
| 421 | GS | Financials | November 2025 | 2025-11-01 | HOLD | 59.6 | up | +4.7% | ➖ |
| 422 | HAL | Energy | November 2025 | 2025-11-01 | BUY | 68.1 | down | -2.3% | ❌ |
| 423 | JNJ | Healthcare | November 2025 | 2025-11-01 | HOLD | 46.7 | up | +10.2% | ➖ |
| 424 | JPM | Financials | November 2025 | 2025-11-01 | BUY | 64.0 | up | +0.6% | ✅ |
| 425 | KO | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 46.1 | up | +6.1% | ➖ |
| 426 | LLY | Healthcare | November 2025 | 2025-11-01 | HOLD | 56.7 | up | +24.8% | ➖ |
| 427 | MA | Financials | November 2025 | 2025-11-01 | HOLD | 45.3 | down | -0.3% | ➖ |
| 428 | MCD | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 49.3 | up | +4.5% | ➖ |
| 429 | META | Technology | November 2025 | 2025-11-01 | BUY | 64.2 | down | -0.1% | ❌ |
| 430 | MO | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 54.3 | up | +4.7% | ➖ |
| 431 | MPC | Energy | November 2025 | 2025-11-01 | HOLD | 43.1 | down | -0.1% | ➖ |
| 432 | MRK | Healthcare | November 2025 | 2025-11-01 | BUY | 63.0 | up | +21.9% | ✅ |
| 433 | MS | Financials | November 2025 | 2025-11-01 | HOLD | 59.8 | up | +3.5% | ➖ |
| 434 | MSFT | Technology | November 2025 | 2025-11-01 | HOLD | 54.4 | down | -4.8% | ➖ |
| 435 | NVDA | Technology | November 2025 | 2025-11-01 | BUY | 64.5 | down | -12.6% | ❌ |
| 436 | ORCL | Technology | November 2025 | 2025-11-01 | HOLD | 43.5 | down | -23.1% | ➖ |
| 437 | OXY | Energy | November 2025 | 2025-11-01 | HOLD | 44.7 | up | +1.9% | ➖ |
| 438 | PEP | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 53.7 | up | +1.8% | ➖ |
| 439 | PFE | Healthcare | November 2025 | 2025-11-01 | BUY | 63.7 | up | +6.3% | ✅ |
| 440 | PG | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 51.5 | down | -1.5% | ➖ |
| 441 | PM | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 47.9 | up | +9.1% | ➖ |
| 442 | PSX | Energy | November 2025 | 2025-11-01 | SELL | 34.1 | up | +1.5% | ❌ |
| 443 | SLB | Energy | November 2025 | 2025-11-01 | BUY | 64.7 | up | +0.5% | ✅ |
| 444 | TSLA | Technology | November 2025 | 2025-11-01 | HOLD | 46.5 | down | -5.8% | ➖ |
| 445 | UNH | Healthcare | November 2025 | 2025-11-01 | HOLD | 43.0 | down | -3.5% | ➖ |
| 446 | V | Financials | November 2025 | 2025-11-01 | HOLD | 53.4 | down | -1.6% | ➖ |
| 447 | VLO | Energy | November 2025 | 2025-11-01 | HOLD | 44.9 | up | +4.9% | ➖ |
| 448 | WFC | Financials | November 2025 | 2025-11-01 | HOLD | 52.7 | down | -0.8% | ➖ |
| 449 | WMT | Consumer_Staples | November 2025 | 2025-11-01 | HOLD | 55.5 | up | +9.2% | ➖ |
| 450 | XOM | Energy | November 2025 | 2025-11-01 | HOLD | 48.5 | up | +2.2% | ➖ |
| 451 | AAPL | Technology | December 2025 | 2025-12-01 | HOLD | 53.0 | down | -2.1% | ➖ |
| 452 | ABBV | Healthcare | December 2025 | 2025-12-01 | SELL | 29.3 | up | +0.9% | ❌ |
| 453 | ABT | Healthcare | December 2025 | 2025-12-01 | HOLD | 54.0 | down | -2.4% | ➖ |
| 454 | AMZN | Technology | December 2025 | 2025-12-01 | HOLD | 49.0 | down | -0.3% | ➖ |
| 455 | ANET | Technology | December 2025 | 2025-12-01 | BUY | 66.8 | up | +1.4% | ✅ |
| 456 | AXP | Financials | December 2025 | 2025-12-01 | BUY | 67.5 | up | +2.2% | ✅ |
| 457 | BAC | Financials | December 2025 | 2025-12-01 | HOLD | 57.9 | up | +3.6% | ➖ |
| 458 | BLK | Financials | December 2025 | 2025-12-01 | HOLD | 56.0 | up | +3.9% | ➖ |
| 459 | BMY | Healthcare | December 2025 | 2025-12-01 | HOLD | 53.5 | up | +10.2% | ➖ |
| 460 | C | Financials | December 2025 | 2025-12-01 | HOLD | 47.2 | up | +13.1% | ➖ |
| 461 | CI | Healthcare | December 2025 | 2025-12-01 | HOLD | 50.3 | up | +0.3% | ➖ |
| 462 | CL | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 59.2 | down | -1.1% | ➖ |
| 463 | COP | Energy | December 2025 | 2025-12-01 | HOLD | 53.0 | up | +6.1% | ➖ |
| 464 | COST | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 47.6 | down | -5.2% | ➖ |
| 465 | CRM | Technology | December 2025 | 2025-12-01 | HOLD | 53.2 | up | +15.5% | ➖ |
| 466 | CVS | Healthcare | December 2025 | 2025-12-01 | HOLD | 52.1 | down | -0.6% | ➖ |
| 467 | CVX | Energy | December 2025 | 2025-12-01 | HOLD | 43.8 | up | +0.8% | ➖ |
| 468 | EOG | Energy | December 2025 | 2025-12-01 | BUY | 70.9 | down | -2.0% | ❌ |
| 469 | GIS | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 49.3 | down | -1.4% | ➖ |
| 470 | GOOGL | Technology | December 2025 | 2025-12-01 | HOLD | 56.9 | down | -1.9% | ➖ |
| 471 | GS | Financials | December 2025 | 2025-12-01 | HOLD | 59.6 | up | +7.6% | ➖ |
| 472 | HAL | Energy | December 2025 | 2025-12-01 | BUY | 68.1 | up | +9.3% | ✅ |
| 473 | JNJ | Healthcare | December 2025 | 2025-12-01 | HOLD | 46.7 | down | -0.0% | ➖ |
| 474 | JPM | Financials | December 2025 | 2025-12-01 | BUY | 64.0 | up | +3.3% | ✅ |
| 475 | KO | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 46.2 | down | -3.5% | ➖ |
| 476 | LLY | Healthcare | December 2025 | 2025-12-01 | HOLD | 56.7 | up | +0.4% | ➖ |
| 477 | MA | Financials | December 2025 | 2025-12-01 | HOLD | 45.3 | up | +4.9% | ➖ |
| 478 | MCD | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 49.4 | down | -0.6% | ➖ |
| 479 | META | Technology | December 2025 | 2025-12-01 | BUY | 64.2 | up | +2.9% | ✅ |
| 480 | MO | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 54.4 | down | -0.3% | ➖ |
| 481 | MPC | Energy | December 2025 | 2025-12-01 | HOLD | 43.1 | down | -15.4% | ➖ |
| 482 | MRK | Healthcare | December 2025 | 2025-12-01 | HOLD | 60.7 | up | +2.0% | ➖ |
| 483 | MS | Financials | December 2025 | 2025-12-01 | HOLD | 59.8 | up | +5.5% | ➖ |
| 484 | MSFT | Technology | December 2025 | 2025-12-01 | HOLD | 54.4 | down | -0.9% | ➖ |
| 485 | NVDA | Technology | December 2025 | 2025-12-01 | BUY | 64.5 | up | +6.0% | ✅ |
| 486 | ORCL | Technology | December 2025 | 2025-12-01 | HOLD | 42.8 | down | -2.4% | ➖ |
| 487 | OXY | Energy | December 2025 | 2025-12-01 | HOLD | 44.7 | down | -0.7% | ➖ |
| 488 | PEP | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 53.7 | down | -2.1% | ➖ |
| 489 | PFE | Healthcare | December 2025 | 2025-12-01 | BUY | 63.9 | down | -2.9% | ❌ |
| 490 | PG | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 51.5 | down | -2.8% | ➖ |
| 491 | PM | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 45.5 | up | +3.8% | ➖ |
| 492 | PSX | Energy | December 2025 | 2025-12-01 | SELL | 34.1 | down | -5.4% | ✅ |
| 493 | SLB | Energy | December 2025 | 2025-12-01 | BUY | 64.7 | up | +7.2% | ✅ |
| 494 | TSLA | Technology | December 2025 | 2025-12-01 | HOLD | 46.5 | up | +5.6% | ➖ |
| 495 | UNH | Healthcare | December 2025 | 2025-12-01 | HOLD | 43.0 | up | +1.4% | ➖ |
| 496 | V | Financials | December 2025 | 2025-12-01 | HOLD | 40.2 | up | +5.7% | ➖ |
| 497 | VLO | Energy | December 2025 | 2025-12-01 | HOLD | 45.0 | down | -6.7% | ➖ |
| 498 | WFC | Financials | December 2025 | 2025-12-01 | HOLD | 52.7 | up | +9.8% | ➖ |
| 499 | WMT | Consumer_Staples | December 2025 | 2025-12-01 | HOLD | 55.5 | up | +1.5% | ➖ |
| 500 | XOM | Energy | December 2025 | 2025-12-01 | HOLD | 48.5 | up | +4.4% | ➖ |
| 501 | AAPL | Technology | January 2026 | 2026-01-01 | HOLD | 53.0 | down | -4.5% | ➖ |
| 502 | ABBV | Healthcare | January 2026 | 2026-01-01 | SELL | 29.3 | down | -1.6% | ✅ |
| 503 | ABT | Healthcare | January 2026 | 2026-01-01 | HOLD | 56.4 | down | -12.3% | ➖ |
| 504 | AMZN | Technology | January 2026 | 2026-01-01 | HOLD | 49.0 | up | +3.7% | ➖ |
| 505 | ANET | Technology | January 2026 | 2026-01-01 | BUY | 66.8 | up | +8.2% | ✅ |
| 506 | AXP | Financials | January 2026 | 2026-01-01 | BUY | 67.5 | down | -4.6% | ❌ |
| 507 | BAC | Financials | January 2026 | 2026-01-01 | HOLD | 57.9 | down | -3.3% | ➖ |
| 508 | BLK | Financials | January 2026 | 2026-01-01 | HOLD | 56.0 | up | +4.5% | ➖ |
| 509 | BMY | Healthcare | January 2026 | 2026-01-01 | HOLD | 48.7 | up | +3.3% | ➖ |
| 510 | C | Financials | January 2026 | 2026-01-01 | HOLD | 47.2 | down | -0.8% | ➖ |
| 511 | CI | Healthcare | January 2026 | 2026-01-01 | HOLD | 50.3 | down | -0.4% | ➖ |
| 512 | CL | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 59.2 | up | +15.0% | ➖ |
| 513 | COP | Energy | January 2026 | 2026-01-01 | HOLD | 53.1 | up | +11.3% | ➖ |
| 514 | COST | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 47.6 | up | +9.2% | ➖ |
| 515 | CRM | Technology | January 2026 | 2026-01-01 | HOLD | 51.0 | down | -19.9% | ➖ |
| 516 | CVS | Healthcare | January 2026 | 2026-01-01 | HOLD | 52.1 | down | -5.3% | ➖ |
| 517 | CVX | Energy | January 2026 | 2026-01-01 | HOLD | 43.8 | up | +16.1% | ➖ |
| 518 | EOG | Energy | January 2026 | 2026-01-01 | BUY | 70.9 | up | +7.8% | ✅ |
| 519 | GIS | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 49.2 | up | +0.9% | ➖ |
| 520 | GOOGL | Technology | January 2026 | 2026-01-01 | HOLD | 56.9 | up | +8.0% | ➖ |
| 521 | GS | Financials | January 2026 | 2026-01-01 | HOLD | 59.6 | up | +6.4% | ➖ |
| 522 | HAL | Energy | January 2026 | 2026-01-01 | BUY | 63.1 | up | +18.6% | ✅ |
| 523 | JNJ | Healthcare | January 2026 | 2026-01-01 | HOLD | 46.7 | up | +9.8% | ➖ |
| 524 | JPM | Financials | January 2026 | 2026-01-01 | BUY | 64.0 | down | -4.6% | ❌ |
| 525 | KO | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 46.1 | up | +7.0% | ➖ |
| 526 | LLY | Healthcare | January 2026 | 2026-01-01 | HOLD | 56.7 | down | -3.5% | ➖ |
| 527 | MA | Financials | January 2026 | 2026-01-01 | HOLD | 45.3 | down | -5.5% | ➖ |
| 528 | MCD | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 49.4 | up | +3.1% | ➖ |
| 529 | META | Technology | January 2026 | 2026-01-01 | BUY | 64.2 | up | +8.6% | ✅ |
| 530 | MO | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 54.4 | up | +7.5% | ➖ |
| 531 | MPC | Energy | January 2026 | 2026-01-01 | HOLD | 43.0 | up | +8.3% | ➖ |
| 532 | MRK | Healthcare | January 2026 | 2026-01-01 | HOLD | 60.8 | up | +4.8% | ➖ |
| 533 | MS | Financials | January 2026 | 2026-01-01 | HOLD | 59.8 | up | +3.5% | ➖ |
| 534 | MSFT | Technology | January 2026 | 2026-01-01 | HOLD | 54.4 | down | -11.0% | ➖ |
| 535 | NVDA | Technology | January 2026 | 2026-01-01 | BUY | 64.5 | up | +2.5% | ✅ |
| 536 | ORCL | Technology | January 2026 | 2026-01-01 | HOLD | 42.6 | down | -15.3% | ➖ |
| 537 | OXY | Energy | January 2026 | 2026-01-01 | HOLD | 44.7 | up | +10.4% | ➖ |
| 538 | PEP | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 53.7 | up | +7.0% | ➖ |
| 539 | PFE | Healthcare | January 2026 | 2026-01-01 | BUY | 63.8 | up | +8.0% | ✅ |
| 540 | PG | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 51.4 | up | +6.7% | ➖ |
| 541 | PM | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 45.6 | up | +11.9% | ➖ |
| 542 | PSX | Energy | January 2026 | 2026-01-01 | SELL | 34.1 | up | +11.2% | ❌ |
| 543 | SLB | Energy | January 2026 | 2026-01-01 | BUY | 64.9 | up | +26.1% | ✅ |
| 544 | TSLA | Technology | January 2026 | 2026-01-01 | HOLD | 46.5 | down | -4.3% | ➖ |
| 545 | UNH | Healthcare | January 2026 | 2026-01-01 | HOLD | 43.0 | down | -13.1% | ➖ |
| 546 | V | Financials | January 2026 | 2026-01-01 | HOLD | 40.2 | down | -8.2% | ➖ |
| 547 | VLO | Energy | January 2026 | 2026-01-01 | HOLD | 44.9 | up | +11.4% | ➖ |
| 548 | WFC | Financials | January 2026 | 2026-01-01 | HOLD | 52.7 | down | -2.9% | ➖ |
| 549 | WMT | Consumer_Staples | January 2026 | 2026-01-01 | HOLD | 55.5 | up | +6.9% | ➖ |
| 550 | XOM | Energy | January 2026 | 2026-01-01 | HOLD | 48.5 | up | +17.5% | ➖ |
| 551 | AAPL | Technology | February 2026 | 2026-02-01 | HOLD | 53.0 | up | +1.9% | ➖ |
| 552 | ABBV | Healthcare | February 2026 | 2026-02-01 | SELL | 29.3 | up | +4.1% | ❌ |
| 553 | ABT | Healthcare | February 2026 | 2026-02-01 | HOLD | 56.1 | up | +6.5% | ➖ |
| 554 | AMZN | Technology | February 2026 | 2026-02-01 | HOLD | 49.0 | down | -12.2% | ➖ |
| 555 | ANET | Technology | February 2026 | 2026-02-01 | BUY | 66.8 | down | -5.8% | ❌ |
| 556 | AXP | Financials | February 2026 | 2026-02-01 | BUY | 67.5 | down | -12.3% | ❌ |
| 557 | BAC | Financials | February 2026 | 2026-02-01 | HOLD | 57.9 | down | -6.3% | ➖ |
| 558 | BLK | Financials | February 2026 | 2026-02-01 | HOLD | 52.0 | down | -5.0% | ➖ |
| 559 | BMY | Healthcare | February 2026 | 2026-02-01 | HOLD | 48.8 | up | +13.3% | ➖ |
| 560 | C | Financials | February 2026 | 2026-02-01 | HOLD | 47.2 | down | -4.3% | ➖ |
| 561 | CI | Healthcare | February 2026 | 2026-02-01 | HOLD | 50.3 | up | +5.7% | ➖ |
| 562 | CL | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 59.2 | up | +9.8% | ➖ |
| 563 | COP | Energy | February 2026 | 2026-02-01 | HOLD | 48.5 | up | +9.7% | ➖ |
| 564 | COST | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 47.6 | up | +7.5% | ➖ |
| 565 | CRM | Technology | February 2026 | 2026-02-01 | HOLD | 53.0 | down | -8.2% | ➖ |
| 566 | CVS | Healthcare | February 2026 | 2026-02-01 | HOLD | 52.1 | up | +7.2% | ➖ |
| 567 | CVX | Energy | February 2026 | 2026-02-01 | HOLD | 43.9 | up | +6.6% | ➖ |
| 568 | EOG | Energy | February 2026 | 2026-02-01 | BUY | 71.0 | up | +10.7% | ✅ |
| 569 | GIS | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 49.3 | down | -2.2% | ➖ |
| 570 | GOOGL | Technology | February 2026 | 2026-02-01 | HOLD | 56.9 | down | -7.8% | ➖ |
| 571 | GS | Financials | February 2026 | 2026-02-01 | HOLD | 59.6 | down | -8.1% | ➖ |
| 572 | HAL | Energy | February 2026 | 2026-02-01 | HOLD | 60.7 | up | +7.4% | ➖ |
| 573 | JNJ | Healthcare | February 2026 | 2026-02-01 | HOLD | 46.7 | up | +9.9% | ➖ |
| 574 | JPM | Financials | February 2026 | 2026-02-01 | BUY | 64.0 | down | -1.8% | ❌ |
| 575 | KO | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 46.3 | up | +9.0% | ➖ |
| 576 | LLY | Healthcare | February 2026 | 2026-02-01 | HOLD | 56.7 | up | +1.6% | ➖ |
| 577 | MA | Financials | February 2026 | 2026-02-01 | HOLD | 45.3 | down | -4.0% | ➖ |
| 578 | MCD | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 49.4 | up | +8.3% | ➖ |
| 579 | META | Technology | February 2026 | 2026-02-01 | BUY | 64.2 | down | -9.5% | ❌ |
| 580 | MO | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 54.5 | up | +11.4% | ➖ |
| 581 | MPC | Energy | February 2026 | 2026-02-01 | HOLD | 43.0 | up | +13.1% | ➖ |
| 582 | MRK | Healthcare | February 2026 | 2026-02-01 | HOLD | 60.8 | up | +12.3% | ➖ |
| 583 | MS | Financials | February 2026 | 2026-02-01 | HOLD | 59.8 | down | -8.9% | ➖ |
| 584 | MSFT | Technology | February 2026 | 2026-02-01 | HOLD | 54.4 | down | -8.5% | ➖ |
| 585 | NVDA | Technology | February 2026 | 2026-02-01 | BUY | 64.5 | down | -7.3% | ❌ |
| 586 | ORCL | Technology | February 2026 | 2026-02-01 | HOLD | 44.2 | down | -11.7% | ➖ |
| 587 | OXY | Energy | February 2026 | 2026-02-01 | HOLD | 44.7 | up | +16.9% | ➖ |
| 588 | PEP | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 53.8 | up | +10.5% | ➖ |
| 589 | PFE | Healthcare | February 2026 | 2026-02-01 | BUY | 63.9 | up | +4.6% | ✅ |
| 590 | PG | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 51.5 | up | +10.2% | ➖ |
| 591 | PM | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 45.7 | up | +4.1% | ➖ |
| 592 | PSX | Energy | February 2026 | 2026-02-01 | SELL | 34.1 | up | +8.4% | ❌ |
| 593 | SLB | Energy | February 2026 | 2026-02-01 | HOLD | 60.1 | up | +6.7% | ➖ |
| 594 | TSLA | Technology | February 2026 | 2026-02-01 | HOLD | 46.5 | down | -6.5% | ➖ |
| 595 | UNH | Healthcare | February 2026 | 2026-02-01 | HOLD | 47.7 | up | +2.2% | ➖ |
| 596 | V | Financials | February 2026 | 2026-02-01 | HOLD | 40.2 | down | -0.3% | ➖ |
| 597 | VLO | Energy | February 2026 | 2026-02-01 | HOLD | 45.0 | up | +13.5% | ➖ |
| 598 | WFC | Financials | February 2026 | 2026-02-01 | HOLD | 52.7 | down | -9.6% | ➖ |
| 599 | WMT | Consumer_Staples | February 2026 | 2026-02-01 | HOLD | 53.0 | up | +7.4% | ➖ |
| 600 | XOM | Energy | February 2026 | 2026-02-01 | HOLD | 48.7 | up | +8.6% | ➖ |

## 5. Misclassification Report

**Total Misclassifications**: 67 out of 156 directional signals
**Misclassification Rate**: 42.9%

### Misclassification Breakdown

| Type | Count | Description |
|------|-------|-------------|
| False Positive (BUY → DOWN) | 52 | Predicted BUY but market went down |
| False Negative (SELL → UP) | 15 | Predicted SELL but market went up |

### Misclassification Frequency by Sector

| Sector | Misclassifications | FP (BUY→DOWN) | FN (SELL→UP) |
|--------|--------------------|----------------|--------------|
| Technology | 14 | 14 | 0 |
| Healthcare | 17 | 11 | 6 |
| Financials | 14 | 14 | 0 |
| Consumer_Staples | 0 | 0 | 0 |
| Energy | 22 | 13 | 9 |

### Misclassification Frequency by Month

| Month | Misclassifications | FP | FN |
|-------|--------------------|----|----|
| March 2025 | 12 | 12 | 0 |
| April 2025 | 9 | 9 | 0 |
| May 2025 | 6 | 5 | 1 |
| June 2025 | 1 | 0 | 1 |
| July 2025 | 5 | 3 | 2 |
| August 2025 | 4 | 2 | 2 |
| September 2025 | 6 | 4 | 2 |
| October 2025 | 5 | 4 | 1 |
| November 2025 | 6 | 4 | 2 |
| December 2025 | 3 | 2 | 1 |
| January 2026 | 3 | 2 | 1 |
| February 2026 | 7 | 5 | 2 |

### Detailed Misclassification Log

| # | Ticker | Sector | Month | Predicted | Actual | Return % | Score | Band | Market Conditions |
|---|--------|--------|-------|-----------|--------|----------|-------|------|-------------------|
| 1 | EOG | Energy | March 2025 | BUY | down | -0.3% | 66.1 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=61.8, graham=8... |
| 2 | EOG | Energy | April 2025 | BUY | down | -11.1% | 66.1 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=61.9, graham=8... |
| 3 | EOG | Energy | May 2025 | BUY | down | -1.6% | 70.9 | good | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=60.4, graham=1... |
| 4 | EOG | Energy | September 2025 | BUY | down | -9.2% | 66.1 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=61.8, graham=8... |
| 5 | EOG | Energy | October 2025 | BUY | down | -5.0% | 71.0 | good | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=60.6, graham=1... |
| 6 | EOG | Energy | December 2025 | BUY | down | -2.0% | 70.9 | good | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=44.4, altman=60.3, graham=1... |
| 7 | HAL | Energy | March 2025 | BUY | down | -4.3% | 68.1 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=55.6, altman=56.9, graham=8... |
| 8 | HAL | Energy | April 2025 | BUY | down | -19.2% | 68.0 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=55.6, altman=56.8, graham=8... |
| 9 | HAL | Energy | May 2025 | BUY | down | -1.2% | 67.9 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=55.6, altman=55.8, graham=8... |
| 10 | HAL | Energy | November 2025 | BUY | down | -2.3% | 68.1 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=55.6, altman=57.1, graham=8... |
| 11 | PSX | Energy | May 2025 | SELL | up | +10.1% | 37.0 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=56.3, graham=33.3... |
| 12 | PSX | Energy | June 2025 | SELL | up | +5.1% | 37.0 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=56.6, graham=33.3... |
| 13 | PSX | Energy | July 2025 | SELL | up | +4.3% | 34.0 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=56.8, graham=33.3... |
| 14 | PSX | Energy | August 2025 | SELL | up | +9.2% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=56.9, graham=33.3... |
| 15 | PSX | Energy | September 2025 | SELL | up | +3.0% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=57.2, graham=33.3... |
| 16 | PSX | Energy | October 2025 | SELL | up | +0.8% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=57.3, graham=33.3... |
| 17 | PSX | Energy | November 2025 | SELL | up | +1.5% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=57.3, graham=33.3... |
| 18 | PSX | Energy | January 2026 | SELL | up | +11.2% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=57.1, graham=33.3... |
| 19 | PSX | Energy | February 2026 | SELL | up | +8.4% | 34.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=55.6, altman=57.5, graham=33.3... |
| 20 | SLB | Energy | April 2025 | BUY | down | -18.4% | 64.9 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=55.5, graham=... |
| 21 | SLB | Energy | May 2025 | BUY | down | -0.6% | 64.4 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=51.3, graham=... |
| 22 | SLB | Energy | September 2025 | BUY | down | -3.9% | 64.7 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=53.9, graham=... |
| 23 | AXP | Financials | March 2025 | BUY | down | -11.8% | 67.5 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=100.0, graham=50.0, growth_prof... |
| 24 | AXP | Financials | April 2025 | BUY | down | -0.4% | 67.5 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=100.0, graham=50.0, growth_prof... |
| 25 | AXP | Financials | July 2025 | BUY | down | -4.6% | 67.5 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=100.0, graham=50.0, growth_prof... |
| 26 | AXP | Financials | January 2026 | BUY | down | -4.6% | 67.5 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=100.0, graham=50.0, growth_prof... |
| 27 | AXP | Financials | February 2026 | BUY | down | -12.3% | 67.5 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=100.0, graham=50.0, growth_prof... |
| 28 | BAC | Financials | March 2025 | BUY | down | -10.0% | 67.9 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=57.1, graham=100.0, growth_prof... |
| 29 | BAC | Financials | April 2025 | BUY | down | -4.2% | 67.9 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=57.1, graham=100.0, growth_prof... |
| 30 | GS | Financials | March 2025 | BUY | down | -12.7% | 63.6 | mixed_positive | DQ={'coverage_ratio': 0.67, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=71.4, graham=50.0, lynch=60... |
| 31 | JPM | Financials | March 2025 | BUY | down | -8.2% | 68.0 | mixed_positive | DQ={'coverage_ratio': 0.67, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=71.4, graham=50.0, lynch=10... |
| 32 | JPM | Financials | October 2025 | BUY | down | -1.4% | 64.0 | mixed_positive | DQ={'coverage_ratio': 0.67, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=71.4, graham=50.0, lynch=80... |
| 33 | JPM | Financials | January 2026 | BUY | down | -4.6% | 64.0 | mixed_positive | DQ={'coverage_ratio': 0.67, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=71.4, graham=50.0, lynch=80... |
| 34 | JPM | Financials | February 2026 | BUY | down | -1.8% | 64.0 | mixed_positive | DQ={'coverage_ratio': 0.67, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=71.4, graham=50.0, lynch=80... |
| 35 | WFC | Financials | March 2025 | BUY | down | -9.7% | 62.7 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=71.4, graham=75.0, growth_profi... |
| 36 | WFC | Financials | April 2025 | BUY | down | -1.0% | 62.7 | mixed_positive | DQ={'coverage_ratio': 0.5, 'coverage_quality': 'low', 'warnings_count': 2}; piotroski=71.4, graham=75.0, growth_profi... |
| 37 | ABBV | Healthcare | July 2025 | SELL | up | +2.9% | 30.9 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=33.6, graham=16.7... |
| 38 | ABBV | Healthcare | August 2025 | SELL | up | +11.3% | 31.0 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=34.4, graham=16.7... |
| 39 | ABBV | Healthcare | September 2025 | SELL | up | +6.1% | 28.9 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=37.9, graham=16.7... |
| 40 | ABBV | Healthcare | November 2025 | SELL | up | +4.4% | 29.1 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=39.5, graham=16.7... |
| 41 | ABBV | Healthcare | December 2025 | SELL | up | +0.9% | 29.3 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=41.1, graham=16.7... |
| 42 | ABBV | Healthcare | February 2026 | SELL | up | +4.1% | 29.3 | weak | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=66.7, altman=40.6, graham=16.7... |
| 43 | MRK | Healthcare | March 2025 | BUY | down | -2.4% | 63.0 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=59.4, graham=3... |
| 44 | MRK | Healthcare | April 2025 | BUY | down | -5.6% | 63.0 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=59.2, graham=3... |
| 45 | MRK | Healthcare | May 2025 | BUY | down | -9.8% | 62.9 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=58.7, graham=3... |
| 46 | MRK | Healthcare | September 2025 | BUY | down | -5.7% | 62.9 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=58.7, graham=3... |
| 47 | PFE | Healthcare | March 2025 | BUY | down | -4.6% | 63.8 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=34.4, graham=... |
| 48 | PFE | Healthcare | April 2025 | BUY | down | -6.1% | 63.7 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=33.8, graham=... |
| 49 | PFE | Healthcare | May 2025 | BUY | down | -1.9% | 68.7 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=33.3, graham=... |
| 50 | PFE | Healthcare | July 2025 | BUY | down | -0.1% | 68.7 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=33.5, graham=... |
| 51 | PFE | Healthcare | September 2025 | BUY | down | -3.7% | 63.8 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=34.0, graham=... |
| 52 | PFE | Healthcare | October 2025 | BUY | down | -4.7% | 63.8 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=34.4, graham=... |
| 53 | PFE | Healthcare | December 2025 | BUY | down | -2.9% | 63.9 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=100.0, altman=34.8, graham=... |
| 54 | ANET | Technology | March 2025 | BUY | down | -16.2% | 69.8 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'medium', 'warnings_count': 3}; piotroski=50.0, altman=70.0, graham=50... |
| 55 | ANET | Technology | November 2025 | BUY | down | -17.1% | 66.8 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'medium', 'warnings_count': 3}; piotroski=50.0, altman=70.0, graham=50... |
| 56 | ANET | Technology | February 2026 | BUY | down | -5.8% | 66.8 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'medium', 'warnings_count': 3}; piotroski=50.0, altman=70.0, graham=50... |
| 57 | META | Technology | March 2025 | BUY | down | -13.6% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 58 | META | Technology | April 2025 | BUY | down | -3.8% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 59 | META | Technology | July 2025 | BUY | down | -5.8% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 60 | META | Technology | August 2025 | BUY | down | -4.5% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 61 | META | Technology | October 2025 | BUY | down | -9.2% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 62 | META | Technology | November 2025 | BUY | down | -0.1% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 63 | META | Technology | February 2026 | BUY | down | -9.5% | 64.2 | mixed_positive | DQ={'coverage_ratio': 1.0, 'coverage_quality': 'high', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=50.0... |
| 64 | NVDA | Technology | March 2025 | BUY | down | -12.2% | 64.5 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=5... |
| 65 | NVDA | Technology | August 2025 | BUY | down | -2.1% | 64.5 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=5... |
| 66 | NVDA | Technology | November 2025 | BUY | down | -12.6% | 64.5 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=5... |
| 67 | NVDA | Technology | February 2026 | BUY | down | -7.3% | 64.5 | mixed_positive | DQ={'coverage_ratio': 0.83, 'coverage_quality': 'medium', 'warnings_count': 2}; piotroski=88.9, altman=70.0, graham=5... |

### Top Misclassified Tickers

| Ticker | Sector | Misclassifications | FP | FN | Avg Return on Misclass |
|--------|--------|--------------------|----|----|-----------------------|
| PSX | Energy | 9 | 0 | 9 | +5.9% |
| PFE | Healthcare | 7 | 7 | 0 | -3.4% |
| META | Technology | 7 | 7 | 0 | -6.7% |
| EOG | Energy | 6 | 6 | 0 | -4.9% |
| ABBV | Healthcare | 6 | 0 | 6 | +4.9% |
| AXP | Financials | 5 | 5 | 0 | -6.7% |
| HAL | Energy | 4 | 4 | 0 | -6.7% |
| JPM | Financials | 4 | 4 | 0 | -4.0% |
| MRK | Healthcare | 4 | 4 | 0 | -5.9% |
| NVDA | Technology | 4 | 4 | 0 | -8.5% |
| SLB | Energy | 3 | 3 | 0 | -7.6% |
| ANET | Technology | 3 | 3 | 0 | -13.1% |
| BAC | Financials | 2 | 2 | 0 | -7.1% |
| WFC | Financials | 2 | 2 | 0 | -5.3% |
| GS | Financials | 1 | 1 | 0 | -12.7% |
