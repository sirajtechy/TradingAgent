# Technical Agent — 12-Month Sector Backtest Report

**Generated**: 2026-03-31 16:00:34
**Window**: March 2025 – February 2026 (12 months)
**Total Periods**: 240
**Total Trades (Directional)**: 193
**Abstentions (HOLD)**: 47

## 1. Performance Summary

| Metric | Value |
|--------|-------|
| Win Rate | 57.0% |
| Sharpe Ratio (annualized) | 0.71 |
| Max Drawdown | 70.51% |
| Profit Factor | 1.68 |
| Total Trades | 193 |
| BUY Signals | 160 |
| SELL Signals | 33 |
| HOLD Signals | 47 |
| Correct | 110 |
| Incorrect | 83 |

## 2. Sector Breakdown

| Sector | Trades | Win Rate | Sharpe | Max DD | Profit Factor | BUY | SELL | HOLD |
|--------|--------|----------|--------|--------|---------------|-----|------|------|
| Technology | 96 | 55.2% | 0.84 | 62.63% | 1.84 | 83 | 13 | 24 |
| Energy | 97 | 58.8% | 0.56 | 49.91% | 1.51 | 77 | 20 | 23 |

## 3. Confusion Matrix

3-class confusion matrix: predicted signal (rows) vs actual market direction (columns).

|              | Actual UP | Actual DOWN | Row Total |
|--------------|-----------|-------------|-----------|
| **Pred BUY**  | 97 (TP) | 63 (FP) | 160 |
| **Pred SELL** | 20 (FN) | 13 (TN) | 33 |
| **Pred HOLD** | 29 (Missed) | 18 (Avoided) | 47 |
| **Col Total** | 146 | 94 | 240 |

### Derived Classification Metrics

| Metric | Value |
|--------|-------|
| Accuracy (TP+TN)/(TP+FP+TN+FN) | 57.0% |
| Precision (TP/(TP+FP)) | 60.6% |
| Recall (TP/(TP+FN)) | 82.9% |
| Specificity (TN/(TN+FP)) | 17.1% |
| F1 Score | 70.0% |
| Abstention Rate | 19.6% |

### Per-Sector Confusion Matrices

#### Technology

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 46 | 37 |
| **Pred SELL** | 6 | 7 |
| **Pred HOLD** | 11 | 13 |

Directional Accuracy: 55.2% (53/96)

#### Energy

|              | Actual UP | Actual DOWN |
|--------------|-----------|-------------|
| **Pred BUY**  | 51 | 26 |
| **Pred SELL** | 14 | 6 |
| **Pred HOLD** | 18 | 5 |

Directional Accuracy: 58.8% (57/97)

## 4. Entry & Exit Signal Log

| # | Ticker | Sector | Month | Signal Date | Signal | Score | Actual Dir | Return % | Correct |
|---|--------|--------|-------|-------------|--------|-------|------------|----------|---------|
| 1 | AAPL | Technology | March 2025 | 2025-03-01 | BUY | 70.4 | down | -9.9% | ❌ |
| 2 | AMZN | Technology | March 2025 | 2025-03-01 | HOLD | 42.5 | down | -9.2% | ➖ |
| 3 | ANET | Technology | March 2025 | 2025-03-01 | HOLD | 36.9 | down | -16.2% | ➖ |
| 4 | COP | Energy | March 2025 | 2025-03-01 | BUY | 54.7 | up | +3.2% | ✅ |
| 5 | CRM | Technology | March 2025 | 2025-03-01 | HOLD | 35.6 | down | -9.4% | ➖ |
| 6 | CVX | Energy | March 2025 | 2025-03-01 | BUY | 87.1 | up | +4.7% | ✅ |
| 7 | EOG | Energy | March 2025 | 2025-03-01 | HOLD | 47.3 | down | -0.3% | ➖ |
| 8 | GOOGL | Technology | March 2025 | 2025-03-01 | HOLD | 36.0 | down | -9.3% | ➖ |
| 9 | HAL | Energy | March 2025 | 2025-03-01 | BUY | 54.4 | down | -4.3% | ❌ |
| 10 | META | Technology | March 2025 | 2025-03-01 | BUY | 57.6 | down | -13.6% | ❌ |
| 11 | MPC | Energy | March 2025 | 2025-03-01 | HOLD | 45.6 | down | -4.0% | ➖ |
| 12 | MSFT | Technology | March 2025 | 2025-03-01 | SELL | 24.6 | down | -4.6% | ✅ |
| 13 | NVDA | Technology | March 2025 | 2025-03-01 | HOLD | 39.9 | down | -12.2% | ➖ |
| 14 | ORCL | Technology | March 2025 | 2025-03-01 | HOLD | 42.7 | down | -15.2% | ➖ |
| 15 | OXY | Energy | March 2025 | 2025-03-01 | HOLD | 47.4 | up | +0.5% | ➖ |
| 16 | PSX | Energy | March 2025 | 2025-03-01 | BUY | 72.9 | down | -6.1% | ❌ |
| 17 | SLB | Energy | March 2025 | 2025-03-01 | BUY | 57.5 | up | +0.5% | ✅ |
| 18 | TSLA | Technology | March 2025 | 2025-03-01 | HOLD | 37.3 | down | -10.1% | ➖ |
| 19 | VLO | Energy | March 2025 | 2025-03-01 | SELL | 27.5 | up | +0.6% | ❌ |
| 20 | XOM | Energy | March 2025 | 2025-03-01 | BUY | 77.8 | up | +5.8% | ✅ |
| 21 | AAPL | Technology | April 2025 | 2025-04-01 | BUY | 64.0 | down | -4.9% | ❌ |
| 22 | AMZN | Technology | April 2025 | 2025-04-01 | HOLD | 36.4 | down | -1.5% | ➖ |
| 23 | ANET | Technology | April 2025 | 2025-04-01 | SELL | 32.0 | up | +4.2% | ❌ |
| 24 | COP | Energy | April 2025 | 2025-04-01 | BUY | 79.4 | down | -12.5% | ❌ |
| 25 | CRM | Technology | April 2025 | 2025-04-01 | SELL | 33.4 | down | -0.1% | ✅ |
| 26 | CVX | Energy | April 2025 | 2025-04-01 | BUY | 83.9 | down | -16.7% | ❌ |
| 27 | EOG | Energy | April 2025 | 2025-04-01 | BUY | 79.5 | down | -11.1% | ❌ |
| 28 | GOOGL | Technology | April 2025 | 2025-04-01 | HOLD | 39.1 | up | +3.6% | ➖ |
| 29 | HAL | Energy | April 2025 | 2025-04-01 | HOLD | 43.6 | down | -19.2% | ➖ |
| 30 | META | Technology | April 2025 | 2025-04-01 | SELL | 33.3 | down | -3.8% | ✅ |
| 31 | MPC | Energy | April 2025 | 2025-04-01 | HOLD | 40.9 | down | -5.1% | ➖ |
| 32 | MSFT | Technology | April 2025 | 2025-04-01 | SELL | 20.4 | up | +5.0% | ❌ |
| 33 | NVDA | Technology | April 2025 | 2025-04-01 | SELL | 27.3 | up | +0.6% | ❌ |
| 34 | ORCL | Technology | April 2025 | 2025-04-01 | SELL | 29.2 | up | +1.1% | ❌ |
| 35 | OXY | Energy | April 2025 | 2025-04-01 | BUY | 64.9 | down | -18.2% | ❌ |
| 36 | PSX | Energy | April 2025 | 2025-04-01 | SELL | 32.6 | down | -14.2% | ✅ |
| 37 | SLB | Energy | April 2025 | 2025-04-01 | BUY | 62.2 | down | -18.4% | ❌ |
| 38 | TSLA | Technology | April 2025 | 2025-04-01 | BUY | 50.5 | up | +12.7% | ✅ |
| 39 | VLO | Energy | April 2025 | 2025-04-01 | BUY | 60.6 | down | -12.5% | ❌ |
| 40 | XOM | Energy | April 2025 | 2025-04-01 | BUY | 84.2 | down | -8.9% | ❌ |
| 41 | AAPL | Technology | May 2025 | 2025-05-01 | BUY | 60.5 | down | -5.4% | ❌ |
| 42 | AMZN | Technology | May 2025 | 2025-05-01 | BUY | 51.9 | up | +11.2% | ✅ |
| 43 | ANET | Technology | May 2025 | 2025-05-01 | BUY | 64.0 | up | +5.3% | ✅ |
| 44 | COP | Energy | May 2025 | 2025-05-01 | HOLD | 37.1 | down | -3.4% | ➖ |
| 45 | CRM | Technology | May 2025 | 2025-05-01 | BUY | 66.4 | down | -1.2% | ❌ |
| 46 | CVX | Energy | May 2025 | 2025-05-01 | HOLD | 37.9 | up | +1.7% | ➖ |
| 47 | EOG | Energy | May 2025 | 2025-05-01 | SELL | 28.3 | down | -1.6% | ✅ |
| 48 | GOOGL | Technology | May 2025 | 2025-05-01 | BUY | 54.0 | up | +8.2% | ✅ |
| 49 | HAL | Energy | May 2025 | 2025-05-01 | SELL | 32.7 | down | -1.2% | ✅ |
| 50 | META | Technology | May 2025 | 2025-05-01 | BUY | 65.8 | up | +17.9% | ✅ |
| 51 | MPC | Energy | May 2025 | 2025-05-01 | BUY | 53.4 | up | +17.6% | ✅ |
| 52 | MSFT | Technology | May 2025 | 2025-05-01 | BUY | 66.1 | up | +16.7% | ✅ |
| 53 | NVDA | Technology | May 2025 | 2025-05-01 | BUY | 55.7 | up | +24.1% | ✅ |
| 54 | ORCL | Technology | May 2025 | 2025-05-01 | BUY | 62.4 | up | +17.6% | ✅ |
| 55 | OXY | Energy | May 2025 | 2025-05-01 | SELL | 29.5 | up | +3.5% | ❌ |
| 56 | PSX | Energy | May 2025 | 2025-05-01 | HOLD | 42.8 | up | +10.1% | ➖ |
| 57 | SLB | Energy | May 2025 | 2025-05-01 | SELL | 24.4 | down | -0.6% | ✅ |
| 58 | TSLA | Technology | May 2025 | 2025-05-01 | BUY | 74.7 | up | +22.8% | ✅ |
| 59 | VLO | Energy | May 2025 | 2025-05-01 | HOLD | 43.7 | up | +12.0% | ➖ |
| 60 | XOM | Energy | May 2025 | 2025-05-01 | SELL | 30.7 | down | -2.3% | ✅ |
| 61 | AAPL | Technology | June 2025 | 2025-06-01 | HOLD | 35.6 | up | +0.1% | ➖ |
| 62 | AMZN | Technology | June 2025 | 2025-06-01 | BUY | 75.6 | up | +8.9% | ✅ |
| 63 | ANET | Technology | June 2025 | 2025-06-01 | HOLD | 37.1 | up | +14.7% | ➖ |
| 64 | COP | Energy | June 2025 | 2025-06-01 | SELL | 32.4 | up | +5.7% | ❌ |
| 65 | CRM | Technology | June 2025 | 2025-06-01 | HOLD | 36.1 | up | +3.2% | ➖ |
| 66 | CVX | Energy | June 2025 | 2025-06-01 | SELL | 30.8 | up | +5.2% | ❌ |
| 67 | EOG | Energy | June 2025 | 2025-06-01 | SELL | 17.2 | up | +11.3% | ❌ |
| 68 | GOOGL | Technology | June 2025 | 2025-06-01 | BUY | 72.3 | up | +4.1% | ✅ |
| 69 | HAL | Energy | June 2025 | 2025-06-01 | SELL | 26.2 | up | +5.9% | ❌ |
| 70 | META | Technology | June 2025 | 2025-06-01 | BUY | 77.1 | up | +13.4% | ✅ |
| 71 | MPC | Energy | June 2025 | 2025-06-01 | BUY | 68.5 | up | +4.2% | ✅ |
| 72 | MSFT | Technology | June 2025 | 2025-06-01 | BUY | 70.1 | up | +7.7% | ✅ |
| 73 | NVDA | Technology | June 2025 | 2025-06-01 | BUY | 70.2 | up | +16.8% | ✅ |
| 74 | ORCL | Technology | June 2025 | 2025-06-01 | BUY | 84.6 | up | +27.0% | ✅ |
| 75 | OXY | Energy | June 2025 | 2025-06-01 | SELL | 25.2 | up | +5.0% | ❌ |
| 76 | PSX | Energy | June 2025 | 2025-06-01 | BUY | 51.7 | up | +5.1% | ✅ |
| 77 | SLB | Energy | June 2025 | 2025-06-01 | SELL | 10.5 | up | +3.8% | ❌ |
| 78 | TSLA | Technology | June 2025 | 2025-06-01 | BUY | 69.2 | down | -6.6% | ❌ |
| 79 | VLO | Energy | June 2025 | 2025-06-01 | HOLD | 47.3 | up | +4.4% | ➖ |
| 80 | XOM | Energy | June 2025 | 2025-06-01 | SELL | 19.1 | up | +6.9% | ❌ |
| 81 | AAPL | Technology | July 2025 | 2025-07-01 | BUY | 64.0 | up | +1.9% | ✅ |
| 82 | AMZN | Technology | July 2025 | 2025-07-01 | BUY | 75.9 | up | +4.9% | ✅ |
| 83 | ANET | Technology | July 2025 | 2025-07-01 | BUY | 84.3 | up | +19.3% | ✅ |
| 84 | COP | Energy | July 2025 | 2025-07-01 | HOLD | 37.9 | up | +7.7% | ➖ |
| 85 | CRM | Technology | July 2025 | 2025-07-01 | BUY | 69.7 | down | -2.9% | ❌ |
| 86 | CVX | Energy | July 2025 | 2025-07-01 | HOLD | 48.0 | up | +7.2% | ➖ |
| 87 | EOG | Energy | July 2025 | 2025-07-01 | BUY | 52.1 | up | +2.2% | ✅ |
| 88 | GOOGL | Technology | July 2025 | 2025-07-01 | BUY | 71.5 | up | +11.5% | ✅ |
| 89 | HAL | Energy | July 2025 | 2025-07-01 | SELL | 29.7 | up | +9.9% | ❌ |
| 90 | META | Technology | July 2025 | 2025-07-01 | BUY | 87.3 | down | -5.8% | ❌ |
| 91 | MPC | Energy | July 2025 | 2025-07-01 | BUY | 61.6 | up | +2.8% | ✅ |
| 92 | MSFT | Technology | July 2025 | 2025-07-01 | BUY | 84.3 | up | +3.2% | ✅ |
| 93 | NVDA | Technology | July 2025 | 2025-07-01 | BUY | 86.5 | up | +13.5% | ✅ |
| 94 | ORCL | Technology | July 2025 | 2025-07-01 | BUY | 79.2 | up | +14.9% | ✅ |
| 95 | OXY | Energy | July 2025 | 2025-07-01 | SELL | 33.6 | up | +5.7% | ❌ |
| 96 | PSX | Energy | July 2025 | 2025-07-01 | HOLD | 46.5 | up | +4.3% | ➖ |
| 97 | SLB | Energy | July 2025 | 2025-07-01 | HOLD | 36.6 | up | +1.1% | ➖ |
| 98 | TSLA | Technology | July 2025 | 2025-07-01 | HOLD | 48.1 | up | +0.4% | ➖ |
| 99 | VLO | Energy | July 2025 | 2025-07-01 | BUY | 56.8 | up | +3.7% | ✅ |
| 100 | XOM | Energy | July 2025 | 2025-07-01 | HOLD | 45.8 | up | +3.8% | ➖ |
| 101 | AAPL | Technology | August 2025 | 2025-08-01 | SELL | 29.7 | up | +12.0% | ❌ |
| 102 | AMZN | Technology | August 2025 | 2025-08-01 | BUY | 82.8 | down | -2.2% | ❌ |
| 103 | ANET | Technology | August 2025 | 2025-08-01 | BUY | 91.1 | up | +10.8% | ✅ |
| 104 | COP | Energy | August 2025 | 2025-08-01 | BUY | 60.8 | up | +4.7% | ✅ |
| 105 | CRM | Technology | August 2025 | 2025-08-01 | HOLD | 39.0 | down | -0.8% | ➖ |
| 106 | CVX | Energy | August 2025 | 2025-08-01 | BUY | 54.4 | up | +7.1% | ✅ |
| 107 | EOG | Energy | August 2025 | 2025-08-01 | BUY | 72.4 | up | +4.0% | ✅ |
| 108 | GOOGL | Technology | August 2025 | 2025-08-01 | BUY | 70.2 | up | +10.9% | ✅ |
| 109 | HAL | Energy | August 2025 | 2025-08-01 | BUY | 63.4 | up | +1.5% | ✅ |
| 110 | META | Technology | August 2025 | 2025-08-01 | BUY | 85.5 | down | -4.5% | ❌ |
| 111 | MPC | Energy | August 2025 | 2025-08-01 | BUY | 55.0 | up | +6.2% | ✅ |
| 112 | MSFT | Technology | August 2025 | 2025-08-01 | BUY | 85.2 | down | -4.9% | ❌ |
| 113 | NVDA | Technology | August 2025 | 2025-08-01 | BUY | 71.1 | down | -2.1% | ❌ |
| 114 | ORCL | Technology | August 2025 | 2025-08-01 | BUY | 80.0 | down | -10.9% | ❌ |
| 115 | OXY | Energy | August 2025 | 2025-08-01 | HOLD | 44.1 | up | +8.3% | ➖ |
| 116 | PSX | Energy | August 2025 | 2025-08-01 | BUY | 52.8 | up | +9.2% | ✅ |
| 117 | SLB | Energy | August 2025 | 2025-08-01 | SELL | 23.5 | up | +9.0% | ❌ |
| 118 | TSLA | Technology | August 2025 | 2025-08-01 | BUY | 50.6 | up | +8.3% | ✅ |
| 119 | VLO | Energy | August 2025 | 2025-08-01 | HOLD | 45.4 | up | +10.7% | ➖ |
| 120 | XOM | Energy | August 2025 | 2025-08-01 | BUY | 70.4 | up | +3.3% | ✅ |
| 121 | AAPL | Technology | September 2025 | 2025-09-01 | BUY | 68.4 | up | +9.6% | ✅ |
| 122 | AMZN | Technology | September 2025 | 2025-09-01 | BUY | 73.6 | down | -3.0% | ❌ |
| 123 | ANET | Technology | September 2025 | 2025-09-01 | BUY | 80.6 | up | +5.0% | ✅ |
| 124 | COP | Energy | September 2025 | 2025-09-01 | BUY | 82.1 | down | -3.1% | ❌ |
| 125 | CRM | Technology | September 2025 | 2025-09-01 | BUY | 68.1 | down | -4.2% | ❌ |
| 126 | CVX | Energy | September 2025 | 2025-09-01 | BUY | 81.4 | down | -2.8% | ❌ |
| 127 | EOG | Energy | September 2025 | 2025-09-01 | BUY | 81.3 | down | -9.2% | ❌ |
| 128 | GOOGL | Technology | September 2025 | 2025-09-01 | BUY | 87.5 | up | +14.7% | ✅ |
| 129 | HAL | Energy | September 2025 | 2025-09-01 | BUY | 73.3 | up | +10.8% | ✅ |
| 130 | META | Technology | September 2025 | 2025-09-01 | HOLD | 45.4 | up | +0.7% | ➖ |
| 131 | MPC | Energy | September 2025 | 2025-09-01 | BUY | 87.4 | up | +9.3% | ✅ |
| 132 | MSFT | Technology | September 2025 | 2025-09-01 | BUY | 59.1 | up | +1.6% | ✅ |
| 133 | NVDA | Technology | September 2025 | 2025-09-01 | BUY | 52.1 | up | +4.4% | ✅ |
| 134 | ORCL | Technology | September 2025 | 2025-09-01 | HOLD | 37.9 | up | +25.0% | ➖ |
| 135 | OXY | Energy | September 2025 | 2025-09-01 | BUY | 82.1 | up | +1.6% | ✅ |
| 136 | PSX | Energy | September 2025 | 2025-09-01 | BUY | 85.2 | up | +3.0% | ✅ |
| 137 | SLB | Energy | September 2025 | 2025-09-01 | BUY | 74.7 | down | -3.9% | ❌ |
| 138 | TSLA | Technology | September 2025 | 2025-09-01 | BUY | 65.8 | up | +32.8% | ✅ |
| 139 | VLO | Energy | September 2025 | 2025-09-01 | BUY | 89.8 | up | +13.2% | ✅ |
| 140 | XOM | Energy | September 2025 | 2025-09-01 | BUY | 87.1 | down | -0.1% | ❌ |
| 141 | AAPL | Technology | October 2025 | 2025-10-01 | BUY | 76.6 | up | +6.6% | ✅ |
| 142 | AMZN | Technology | October 2025 | 2025-10-01 | HOLD | 48.9 | up | +1.5% | ➖ |
| 143 | ANET | Technology | October 2025 | 2025-10-01 | BUY | 77.3 | up | +8.7% | ✅ |
| 144 | COP | Energy | October 2025 | 2025-10-01 | BUY | 61.3 | down | -6.8% | ❌ |
| 145 | CRM | Technology | October 2025 | 2025-10-01 | SELL | 32.9 | up | +8.3% | ❌ |
| 146 | CVX | Energy | October 2025 | 2025-10-01 | BUY | 52.2 | down | -1.1% | ❌ |
| 147 | EOG | Energy | October 2025 | 2025-10-01 | SELL | 15.8 | down | -5.0% | ✅ |
| 148 | GOOGL | Technology | October 2025 | 2025-10-01 | BUY | 61.9 | up | +15.8% | ✅ |
| 149 | HAL | Energy | October 2025 | 2025-10-01 | BUY | 68.9 | up | +9.6% | ✅ |
| 150 | META | Technology | October 2025 | 2025-10-01 | HOLD | 41.7 | down | -9.2% | ➖ |
| 151 | MPC | Energy | October 2025 | 2025-10-01 | BUY | 79.4 | up | +1.5% | ✅ |
| 152 | MSFT | Technology | October 2025 | 2025-10-01 | BUY | 84.9 | up | +1.5% | ✅ |
| 153 | NVDA | Technology | October 2025 | 2025-10-01 | BUY | 82.6 | up | +8.7% | ✅ |
| 154 | ORCL | Technology | October 2025 | 2025-10-01 | BUY | 59.5 | down | -8.5% | ❌ |
| 155 | OXY | Energy | October 2025 | 2025-10-01 | BUY | 81.0 | down | -13.9% | ❌ |
| 156 | PSX | Energy | October 2025 | 2025-10-01 | BUY | 83.2 | up | +0.8% | ✅ |
| 157 | SLB | Energy | October 2025 | 2025-10-01 | SELL | 26.0 | up | +5.7% | ❌ |
| 158 | TSLA | Technology | October 2025 | 2025-10-01 | BUY | 76.6 | down | -1.0% | ❌ |
| 159 | VLO | Energy | October 2025 | 2025-10-01 | BUY | 78.0 | down | -0.1% | ❌ |
| 160 | XOM | Energy | October 2025 | 2025-10-01 | BUY | 56.7 | up | +1.7% | ✅ |
| 161 | AAPL | Technology | November 2025 | 2025-11-01 | BUY | 81.5 | up | +3.2% | ✅ |
| 162 | AMZN | Technology | November 2025 | 2025-11-01 | BUY | 90.8 | down | -4.5% | ❌ |
| 163 | ANET | Technology | November 2025 | 2025-11-01 | BUY | 79.0 | down | -17.1% | ❌ |
| 164 | COP | Energy | November 2025 | 2025-11-01 | HOLD | 49.3 | up | +0.7% | ➖ |
| 165 | CRM | Technology | November 2025 | 2025-11-01 | BUY | 72.1 | down | -11.5% | ❌ |
| 166 | CVX | Energy | November 2025 | 2025-11-01 | BUY | 86.3 | down | -3.1% | ❌ |
| 167 | EOG | Energy | November 2025 | 2025-11-01 | HOLD | 39.3 | up | +1.9% | ➖ |
| 168 | GOOGL | Technology | November 2025 | 2025-11-01 | BUY | 87.5 | up | +13.9% | ✅ |
| 169 | HAL | Energy | November 2025 | 2025-11-01 | BUY | 75.3 | down | -2.3% | ❌ |
| 170 | META | Technology | November 2025 | 2025-11-01 | SELL | 32.0 | down | -0.1% | ✅ |
| 171 | MPC | Energy | November 2025 | 2025-11-01 | BUY | 77.2 | down | -0.1% | ❌ |
| 172 | MSFT | Technology | November 2025 | 2025-11-01 | BUY | 64.9 | down | -4.8% | ❌ |
| 173 | NVDA | Technology | November 2025 | 2025-11-01 | BUY | 83.5 | down | -12.6% | ❌ |
| 174 | ORCL | Technology | November 2025 | 2025-11-01 | HOLD | 46.7 | down | -23.1% | ➖ |
| 175 | OXY | Energy | November 2025 | 2025-11-01 | SELL | 34.7 | up | +1.9% | ❌ |
| 176 | PSX | Energy | November 2025 | 2025-11-01 | BUY | 73.0 | up | +1.5% | ✅ |
| 177 | SLB | Energy | November 2025 | 2025-11-01 | BUY | 66.8 | up | +0.5% | ✅ |
| 178 | TSLA | Technology | November 2025 | 2025-11-01 | BUY | 75.9 | down | -5.8% | ❌ |
| 179 | VLO | Energy | November 2025 | 2025-11-01 | BUY | 77.2 | up | +4.9% | ✅ |
| 180 | XOM | Energy | November 2025 | 2025-11-01 | BUY | 76.4 | up | +2.2% | ✅ |
| 181 | AAPL | Technology | December 2025 | 2025-12-01 | BUY | 86.5 | down | -2.1% | ❌ |
| 182 | AMZN | Technology | December 2025 | 2025-12-01 | BUY | 65.8 | down | -0.3% | ❌ |
| 183 | ANET | Technology | December 2025 | 2025-12-01 | HOLD | 49.0 | up | +1.4% | ➖ |
| 184 | COP | Energy | December 2025 | 2025-12-01 | BUY | 54.3 | up | +6.1% | ✅ |
| 185 | CRM | Technology | December 2025 | 2025-12-01 | HOLD | 40.5 | up | +15.5% | ➖ |
| 186 | CVX | Energy | December 2025 | 2025-12-01 | BUY | 51.2 | up | +0.8% | ✅ |
| 187 | EOG | Energy | December 2025 | 2025-12-01 | BUY | 58.0 | down | -2.0% | ❌ |
| 188 | GOOGL | Technology | December 2025 | 2025-12-01 | BUY | 80.2 | down | -1.9% | ❌ |
| 189 | HAL | Energy | December 2025 | 2025-12-01 | BUY | 67.2 | up | +9.3% | ✅ |
| 190 | META | Technology | December 2025 | 2025-12-01 | BUY | 57.5 | up | +2.9% | ✅ |
| 191 | MPC | Energy | December 2025 | 2025-12-01 | BUY | 70.0 | down | -15.4% | ❌ |
| 192 | MSFT | Technology | December 2025 | 2025-12-01 | BUY | 51.0 | down | -0.9% | ❌ |
| 193 | NVDA | Technology | December 2025 | 2025-12-01 | HOLD | 46.6 | up | +6.0% | ➖ |
| 194 | ORCL | Technology | December 2025 | 2025-12-01 | HOLD | 42.2 | down | -2.4% | ➖ |
| 195 | OXY | Energy | December 2025 | 2025-12-01 | BUY | 57.0 | down | -0.7% | ❌ |
| 196 | PSX | Energy | December 2025 | 2025-12-01 | BUY | 77.1 | down | -5.4% | ❌ |
| 197 | SLB | Energy | December 2025 | 2025-12-01 | BUY | 64.3 | up | +7.2% | ✅ |
| 198 | TSLA | Technology | December 2025 | 2025-12-01 | BUY | 76.9 | up | +5.6% | ✅ |
| 199 | VLO | Energy | December 2025 | 2025-12-01 | BUY | 76.3 | down | -6.7% | ❌ |
| 200 | XOM | Energy | December 2025 | 2025-12-01 | BUY | 65.2 | up | +4.4% | ✅ |
| 201 | AAPL | Technology | January 2026 | 2026-01-01 | BUY | 52.4 | down | -4.5% | ❌ |
| 202 | AMZN | Technology | January 2026 | 2026-01-01 | BUY | 74.9 | up | +3.7% | ✅ |
| 203 | ANET | Technology | January 2026 | 2026-01-01 | BUY | 62.6 | up | +8.2% | ✅ |
| 204 | COP | Energy | January 2026 | 2026-01-01 | BUY | 70.8 | up | +11.3% | ✅ |
| 205 | CRM | Technology | January 2026 | 2026-01-01 | BUY | 73.9 | down | -19.9% | ❌ |
| 206 | CVX | Energy | January 2026 | 2026-01-01 | BUY | 84.5 | up | +16.1% | ✅ |
| 207 | EOG | Energy | January 2026 | 2026-01-01 | HOLD | 42.0 | up | +7.8% | ➖ |
| 208 | GOOGL | Technology | January 2026 | 2026-01-01 | BUY | 75.3 | up | +8.0% | ✅ |
| 209 | HAL | Energy | January 2026 | 2026-01-01 | BUY | 73.5 | up | +18.6% | ✅ |
| 210 | META | Technology | January 2026 | 2026-01-01 | BUY | 53.9 | up | +8.6% | ✅ |
| 211 | MPC | Energy | January 2026 | 2026-01-01 | HOLD | 37.7 | up | +8.3% | ➖ |
| 212 | MSFT | Technology | January 2026 | 2026-01-01 | BUY | 53.6 | down | -11.0% | ❌ |
| 213 | NVDA | Technology | January 2026 | 2026-01-01 | BUY | 76.4 | up | +2.5% | ✅ |
| 214 | ORCL | Technology | January 2026 | 2026-01-01 | BUY | 55.8 | down | -15.3% | ❌ |
| 215 | OXY | Energy | January 2026 | 2026-01-01 | BUY | 58.3 | up | +10.4% | ✅ |
| 216 | PSX | Energy | January 2026 | 2026-01-01 | HOLD | 43.4 | up | +11.2% | ➖ |
| 217 | SLB | Energy | January 2026 | 2026-01-01 | BUY | 68.9 | up | +26.1% | ✅ |
| 218 | TSLA | Technology | January 2026 | 2026-01-01 | BUY | 52.2 | down | -4.3% | ❌ |
| 219 | VLO | Energy | January 2026 | 2026-01-01 | HOLD | 46.1 | up | +11.4% | ➖ |
| 220 | XOM | Energy | January 2026 | 2026-01-01 | BUY | 80.3 | up | +17.5% | ✅ |
| 221 | AAPL | Technology | February 2026 | 2026-02-01 | BUY | 67.7 | up | +1.9% | ✅ |
| 222 | AMZN | Technology | February 2026 | 2026-02-01 | BUY | 72.3 | down | -12.2% | ❌ |
| 223 | ANET | Technology | February 2026 | 2026-02-01 | BUY | 75.8 | down | -5.8% | ❌ |
| 224 | COP | Energy | February 2026 | 2026-02-01 | BUY | 80.0 | up | +9.7% | ✅ |
| 225 | CRM | Technology | February 2026 | 2026-02-01 | SELL | 24.1 | down | -8.2% | ✅ |
| 226 | CVX | Energy | February 2026 | 2026-02-01 | BUY | 85.1 | up | +6.6% | ✅ |
| 227 | EOG | Energy | February 2026 | 2026-02-01 | BUY | 80.8 | up | +10.7% | ✅ |
| 228 | GOOGL | Technology | February 2026 | 2026-02-01 | BUY | 83.3 | down | -7.8% | ❌ |
| 229 | HAL | Energy | February 2026 | 2026-02-01 | BUY | 68.4 | up | +7.4% | ✅ |
| 230 | META | Technology | February 2026 | 2026-02-01 | BUY | 84.8 | down | -9.5% | ❌ |
| 231 | MPC | Energy | February 2026 | 2026-02-01 | BUY | 72.2 | up | +13.1% | ✅ |
| 232 | MSFT | Technology | February 2026 | 2026-02-01 | SELL | 17.5 | down | -8.5% | ✅ |
| 233 | NVDA | Technology | February 2026 | 2026-02-01 | BUY | 86.3 | down | -7.3% | ❌ |
| 234 | ORCL | Technology | February 2026 | 2026-02-01 | SELL | 27.0 | down | -11.7% | ✅ |
| 235 | OXY | Energy | February 2026 | 2026-02-01 | BUY | 81.1 | up | +16.9% | ✅ |
| 236 | PSX | Energy | February 2026 | 2026-02-01 | BUY | 87.4 | up | +8.4% | ✅ |
| 237 | SLB | Energy | February 2026 | 2026-02-01 | BUY | 67.1 | up | +6.7% | ✅ |
| 238 | TSLA | Technology | February 2026 | 2026-02-01 | HOLD | 48.0 | down | -6.5% | ➖ |
| 239 | VLO | Energy | February 2026 | 2026-02-01 | BUY | 58.2 | up | +13.5% | ✅ |
| 240 | XOM | Energy | February 2026 | 2026-02-01 | BUY | 81.5 | up | +8.6% | ✅ |

## 5. Misclassification Report

**Total Misclassifications**: 83 out of 193 directional signals
**Misclassification Rate**: 43.0%

### Misclassification Breakdown

| Type | Count | Description |
|------|-------|-------------|
| False Positive (BUY → DOWN) | 63 | Predicted BUY but market went down |
| False Negative (SELL → UP) | 20 | Predicted SELL but market went up |

### Misclassification Frequency by Sector

| Sector | Misclassifications | FP (BUY→DOWN) | FN (SELL→UP) |
|--------|--------------------|----------------|--------------|
| Technology | 43 | 37 | 6 |
| Healthcare | 0 | 0 | 0 |
| Financials | 0 | 0 | 0 |
| Consumer_Staples | 0 | 0 | 0 |
| Energy | 40 | 26 | 14 |

### Misclassification Frequency by Month

| Month | Misclassifications | FP | FN |
|-------|--------------------|----|----|
| March 2025 | 5 | 4 | 1 |
| April 2025 | 12 | 8 | 4 |
| May 2025 | 3 | 2 | 1 |
| June 2025 | 8 | 1 | 7 |
| July 2025 | 4 | 2 | 2 |
| August 2025 | 7 | 5 | 2 |
| September 2025 | 7 | 7 | 0 |
| October 2025 | 8 | 6 | 2 |
| November 2025 | 10 | 9 | 1 |
| December 2025 | 9 | 9 | 0 |
| January 2026 | 5 | 5 | 0 |
| February 2026 | 5 | 5 | 0 |

### Detailed Misclassification Log

| # | Ticker | Sector | Month | Predicted | Actual | Return % | Score | Band | Market Conditions |
|---|--------|--------|-------|-----------|--------|----------|-------|------|-------------------|
| 1 | COP | Energy | April 2025 | BUY | down | -12.5% | 79.4 | strong | ema_trend=77.5, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=50.0, adx_stochastic=63.0, pattern_reco... |
| 2 | COP | Energy | June 2025 | SELL | up | +5.7% | 32.4 | weak | ema_trend=0.0, macd_system=33.0, rsi_regime=58.0, bollinger=46.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 3 | COP | Energy | September 2025 | BUY | down | -3.1% | 82.1 | strong | ema_trend=77.5, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=63.0, pattern_reco... |
| 4 | COP | Energy | October 2025 | BUY | down | -6.8% | 61.3 | good | ema_trend=47.5, macd_system=67.0, rsi_regime=58.0, bollinger=69.0, volume_obv=35.0, adx_stochastic=53.0, pattern_reco... |
| 5 | CVX | Energy | April 2025 | BUY | down | -16.7% | 83.9 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=68.0, pattern_rec... |
| 6 | CVX | Energy | June 2025 | SELL | up | +5.2% | 30.8 | weak | ema_trend=0.0, macd_system=30.0, rsi_regime=58.0, bollinger=35.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 7 | CVX | Energy | September 2025 | BUY | down | -2.8% | 81.4 | strong | ema_trend=100.0, macd_system=74.0, rsi_regime=69.0, bollinger=80.0, volume_obv=65.0, adx_stochastic=68.0, pattern_rec... |
| 8 | CVX | Energy | October 2025 | BUY | down | -1.1% | 52.2 | mixed_positive | ema_trend=85.0, macd_system=37.0, rsi_regime=38.0, bollinger=25.0, volume_obv=20.0, adx_stochastic=37.0, pattern_reco... |
| 9 | CVX | Energy | November 2025 | BUY | down | -3.1% | 86.3 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_rec... |
| 10 | EOG | Energy | April 2025 | BUY | down | -11.1% | 79.5 | strong | ema_trend=92.5, macd_system=87.0, rsi_regime=62.0, bollinger=79.0, volume_obv=65.0, adx_stochastic=53.0, pattern_reco... |
| 11 | EOG | Energy | June 2025 | SELL | up | +11.3% | 17.2 | weak | ema_trend=0.0, macd_system=0.0, rsi_regime=18.0, bollinger=46.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recogn... |
| 12 | EOG | Energy | September 2025 | BUY | down | -9.2% | 81.3 | strong | ema_trend=77.5, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 13 | EOG | Energy | December 2025 | BUY | down | -2.0% | 58.0 | mixed_positive | ema_trend=15.0, macd_system=63.0, rsi_regime=95.0, bollinger=59.0, volume_obv=35.0, adx_stochastic=43.0, pattern_reco... |
| 14 | HAL | Energy | March 2025 | BUY | down | -4.3% | 54.4 | mixed_positive | ema_trend=0.0, macd_system=76.0, rsi_regime=58.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=27.0, pattern_recog... |
| 15 | HAL | Energy | June 2025 | SELL | up | +5.9% | 26.2 | weak | ema_trend=0.0, macd_system=13.0, rsi_regime=18.0, bollinger=36.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 16 | HAL | Energy | July 2025 | SELL | up | +9.9% | 29.7 | weak | ema_trend=0.0, macd_system=13.0, rsi_regime=38.0, bollinger=35.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 17 | HAL | Energy | November 2025 | BUY | down | -2.3% | 75.3 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=49.0, bollinger=70.0, volume_obv=80.0, adx_stochastic=51.0, pattern_rec... |
| 18 | MPC | Energy | November 2025 | BUY | down | -0.1% | 77.2 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=70.0, volume_obv=65.0, adx_stochastic=63.0, pattern_rec... |
| 19 | MPC | Energy | December 2025 | BUY | down | -15.4% | 70.0 | good | ema_trend=100.0, macd_system=44.0, rsi_regime=69.0, bollinger=80.0, volume_obv=35.0, adx_stochastic=27.0, pattern_rec... |
| 20 | OXY | Energy | April 2025 | BUY | down | -18.2% | 64.9 | good | ema_trend=40.0, macd_system=67.0, rsi_regime=82.0, bollinger=80.0, volume_obv=35.0, adx_stochastic=53.0, pattern_reco... |
| 21 | OXY | Energy | May 2025 | SELL | up | +3.5% | 29.5 | weak | ema_trend=0.0, macd_system=43.0, rsi_regime=25.0, bollinger=35.0, volume_obv=50.0, adx_stochastic=30.0, pattern_recog... |
| 22 | OXY | Energy | June 2025 | SELL | up | +5.0% | 25.2 | weak | ema_trend=0.0, macd_system=13.0, rsi_regime=38.0, bollinger=35.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 23 | OXY | Energy | July 2025 | SELL | up | +5.7% | 33.6 | weak | ema_trend=7.5, macd_system=37.0, rsi_regime=38.0, bollinger=35.0, volume_obv=5.0, adx_stochastic=27.0, pattern_recogn... |
| 24 | OXY | Energy | October 2025 | BUY | down | -13.9% | 81.0 | strong | ema_trend=92.5, macd_system=67.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 25 | OXY | Energy | November 2025 | SELL | up | +1.9% | 34.7 | weak | ema_trend=15.0, macd_system=33.0, rsi_regime=18.0, bollinger=35.0, volume_obv=65.0, adx_stochastic=59.0, pattern_reco... |
| 26 | OXY | Energy | December 2025 | BUY | down | -0.7% | 57.0 | mixed_positive | ema_trend=15.0, macd_system=63.0, rsi_regime=82.0, bollinger=69.0, volume_obv=35.0, adx_stochastic=43.0, pattern_reco... |
| 27 | PSX | Energy | March 2025 | BUY | down | -6.1% | 72.9 | good | ema_trend=77.5, macd_system=87.0, rsi_regime=69.0, bollinger=69.0, volume_obv=20.0, adx_stochastic=63.0, pattern_reco... |
| 28 | PSX | Energy | December 2025 | BUY | down | -5.4% | 77.1 | strong | ema_trend=100.0, macd_system=44.0, rsi_regime=82.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=53.0, pattern_rec... |
| 29 | SLB | Energy | April 2025 | BUY | down | -18.4% | 62.2 | good | ema_trend=47.5, macd_system=67.0, rsi_regime=62.0, bollinger=70.0, volume_obv=35.0, adx_stochastic=53.0, pattern_reco... |
| 30 | SLB | Energy | June 2025 | SELL | up | +3.8% | 10.5 | weak | ema_trend=0.0, macd_system=0.0, rsi_regime=18.0, bollinger=36.0, volume_obv=5.0, adx_stochastic=27.0, pattern_recogni... |
| 31 | SLB | Energy | August 2025 | SELL | up | +9.0% | 23.5 | weak | ema_trend=0.0, macd_system=13.0, rsi_regime=25.0, bollinger=15.0, volume_obv=50.0, adx_stochastic=27.0, pattern_recog... |
| 32 | SLB | Energy | September 2025 | BUY | down | -3.9% | 74.7 | good | ema_trend=47.5, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 33 | SLB | Energy | October 2025 | SELL | up | +5.7% | 26.0 | weak | ema_trend=7.5, macd_system=13.0, rsi_regime=38.0, bollinger=35.0, volume_obv=20.0, adx_stochastic=37.0, pattern_recog... |
| 34 | VLO | Energy | March 2025 | SELL | up | +0.6% | 27.5 | weak | ema_trend=7.5, macd_system=26.0, rsi_regime=38.0, bollinger=36.0, volume_obv=35.0, adx_stochastic=27.0, pattern_recog... |
| 35 | VLO | Energy | April 2025 | BUY | down | -12.5% | 60.6 | good | ema_trend=40.0, macd_system=67.0, rsi_regime=62.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 36 | VLO | Energy | October 2025 | BUY | down | -0.1% | 78.0 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=70.0, volume_obv=65.0, adx_stochastic=73.0, pattern_rec... |
| 37 | VLO | Energy | December 2025 | BUY | down | -6.7% | 76.3 | strong | ema_trend=100.0, macd_system=44.0, rsi_regime=82.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=43.0, pattern_rec... |
| 38 | XOM | Energy | April 2025 | BUY | down | -8.9% | 84.2 | strong | ema_trend=85.0, macd_system=80.0, rsi_regime=82.0, bollinger=80.0, volume_obv=95.0, adx_stochastic=68.0, pattern_reco... |
| 39 | XOM | Energy | June 2025 | SELL | up | +6.9% | 19.1 | weak | ema_trend=0.0, macd_system=33.0, rsi_regime=18.0, bollinger=46.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 40 | XOM | Energy | September 2025 | BUY | down | -0.1% | 87.1 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=63.0, pattern_rec... |
| 41 | AAPL | Technology | March 2025 | BUY | down | -9.9% | 70.4 | good | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=59.0, volume_obv=20.0, adx_stochastic=47.0, pattern_rec... |
| 42 | AAPL | Technology | April 2025 | BUY | down | -4.9% | 64.0 | good | ema_trend=52.5, macd_system=63.0, rsi_regime=58.0, bollinger=59.0, volume_obv=80.0, adx_stochastic=47.0, pattern_reco... |
| 43 | AAPL | Technology | May 2025 | BUY | down | -5.4% | 60.5 | good | ema_trend=15.0, macd_system=63.0, rsi_regime=82.0, bollinger=59.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 44 | AAPL | Technology | August 2025 | SELL | up | +12.0% | 29.7 | weak | ema_trend=7.5, macd_system=24.0, rsi_regime=25.0, bollinger=25.0, volume_obv=20.0, adx_stochastic=27.0, pattern_recog... |
| 45 | AAPL | Technology | December 2025 | BUY | down | -2.1% | 86.5 | strong | ema_trend=100.0, macd_system=74.0, rsi_regime=82.0, bollinger=80.0, volume_obv=95.0, adx_stochastic=68.0, pattern_rec... |
| 46 | AAPL | Technology | January 2026 | BUY | down | -4.5% | 52.4 | mixed_positive | ema_trend=85.0, macd_system=20.0, rsi_regime=38.0, bollinger=25.0, volume_obv=65.0, adx_stochastic=27.0, pattern_reco... |
| 47 | AMZN | Technology | August 2025 | BUY | down | -2.2% | 82.8 | strong | ema_trend=100.0, macd_system=74.0, rsi_regime=62.0, bollinger=90.0, volume_obv=80.0, adx_stochastic=68.0, pattern_rec... |
| 48 | AMZN | Technology | September 2025 | BUY | down | -3.0% | 73.6 | good | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=69.0, volume_obv=35.0, adx_stochastic=53.0, pattern_rec... |
| 49 | AMZN | Technology | November 2025 | BUY | down | -4.5% | 90.8 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=95.0, bollinger=80.0, volume_obv=95.0, adx_stochastic=63.0, pattern_rec... |
| 50 | AMZN | Technology | December 2025 | BUY | down | -0.3% | 65.8 | good | ema_trend=100.0, macd_system=33.0, rsi_regime=82.0, bollinger=35.0, volume_obv=35.0, adx_stochastic=43.0, pattern_rec... |
| 51 | AMZN | Technology | February 2026 | BUY | down | -12.2% | 72.3 | good | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=59.0, volume_obv=35.0, adx_stochastic=53.0, pattern_rec... |
| 52 | ANET | Technology | April 2025 | SELL | up | +4.2% | 32.0 | weak | ema_trend=22.5, macd_system=43.0, rsi_regime=18.0, bollinger=15.0, volume_obv=20.0, adx_stochastic=42.0, pattern_reco... |
| 53 | ANET | Technology | November 2025 | BUY | down | -17.1% | 79.0 | strong | ema_trend=100.0, macd_system=54.0, rsi_regime=82.0, bollinger=70.0, volume_obv=95.0, adx_stochastic=36.0, pattern_rec... |
| 54 | ANET | Technology | February 2026 | BUY | down | -5.8% | 75.8 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=70.0, volume_obv=65.0, adx_stochastic=46.0, pattern_rec... |
| 55 | CRM | Technology | May 2025 | BUY | down | -1.2% | 66.4 | good | ema_trend=15.0, macd_system=76.0, rsi_regime=95.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=52.0, pattern_reco... |
| 56 | CRM | Technology | July 2025 | BUY | down | -2.9% | 69.7 | good | ema_trend=40.0, macd_system=63.0, rsi_regime=95.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=53.0, pattern_reco... |
| 57 | CRM | Technology | September 2025 | BUY | down | -4.2% | 68.1 | good | ema_trend=40.0, macd_system=63.0, rsi_regime=82.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=63.0, pattern_reco... |
| 58 | CRM | Technology | October 2025 | SELL | up | +8.3% | 32.9 | weak | ema_trend=0.0, macd_system=26.0, rsi_regime=38.0, bollinger=15.0, volume_obv=65.0, adx_stochastic=27.0, pattern_recog... |
| 59 | CRM | Technology | November 2025 | BUY | down | -11.5% | 72.1 | good | ema_trend=47.5, macd_system=74.0, rsi_regime=82.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=68.0, pattern_reco... |
| 60 | CRM | Technology | January 2026 | BUY | down | -19.9% | 73.9 | good | ema_trend=77.5, macd_system=67.0, rsi_regime=62.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=68.0, pattern_reco... |
| 61 | GOOGL | Technology | December 2025 | BUY | down | -1.9% | 80.2 | strong | ema_trend=100.0, macd_system=54.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=51.0, pattern_rec... |
| 62 | GOOGL | Technology | February 2026 | BUY | down | -7.8% | 83.3 | strong | ema_trend=100.0, macd_system=74.0, rsi_regime=82.0, bollinger=69.0, volume_obv=80.0, adx_stochastic=63.0, pattern_rec... |
| 63 | META | Technology | March 2025 | BUY | down | -13.6% | 57.6 | mixed_positive | ema_trend=85.0, macd_system=57.0, rsi_regime=38.0, bollinger=36.0, volume_obv=20.0, adx_stochastic=42.0, pattern_reco... |
| 64 | META | Technology | July 2025 | BUY | down | -5.8% | 87.3 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=82.0, bollinger=79.0, volume_obv=80.0, adx_stochastic=68.0, pattern_rec... |
| 65 | META | Technology | August 2025 | BUY | down | -4.5% | 85.5 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=43.0, pattern_rec... |
| 66 | META | Technology | February 2026 | BUY | down | -9.5% | 84.8 | strong | ema_trend=77.5, macd_system=100.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=68.0, pattern_rec... |
| 67 | MSFT | Technology | April 2025 | SELL | up | +5.0% | 20.4 | weak | ema_trend=0.0, macd_system=43.0, rsi_regime=18.0, bollinger=36.0, volume_obv=20.0, adx_stochastic=37.0, pattern_recog... |
| 68 | MSFT | Technology | August 2025 | BUY | down | -4.9% | 85.2 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=67.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=73.0, pattern_rec... |
| 69 | MSFT | Technology | November 2025 | BUY | down | -4.8% | 64.9 | good | ema_trend=85.0, macd_system=67.0, rsi_regime=38.0, bollinger=46.0, volume_obv=65.0, adx_stochastic=43.0, pattern_reco... |
| 70 | MSFT | Technology | December 2025 | BUY | down | -0.9% | 51.0 | mixed_positive | ema_trend=52.5, macd_system=33.0, rsi_regime=58.0, bollinger=35.0, volume_obv=35.0, adx_stochastic=42.0, pattern_reco... |
| 71 | MSFT | Technology | January 2026 | BUY | down | -11.0% | 53.6 | mixed_positive | ema_trend=52.5, macd_system=30.0, rsi_regime=38.0, bollinger=69.0, volume_obv=65.0, adx_stochastic=37.0, pattern_reco... |
| 72 | NVDA | Technology | April 2025 | SELL | up | +0.6% | 27.3 | weak | ema_trend=7.5, macd_system=13.0, rsi_regime=18.0, bollinger=15.0, volume_obv=35.0, adx_stochastic=37.0, pattern_recog... |
| 73 | NVDA | Technology | August 2025 | BUY | down | -2.1% | 71.1 | good | ema_trend=100.0, macd_system=37.0, rsi_regime=62.0, bollinger=79.0, volume_obv=35.0, adx_stochastic=73.0, pattern_rec... |
| 74 | NVDA | Technology | November 2025 | BUY | down | -12.6% | 83.5 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=63.0, pattern_rec... |
| 75 | NVDA | Technology | February 2026 | BUY | down | -7.3% | 86.3 | strong | ema_trend=100.0, macd_system=87.0, rsi_regime=82.0, bollinger=80.0, volume_obv=80.0, adx_stochastic=53.0, pattern_rec... |
| 76 | ORCL | Technology | April 2025 | SELL | up | +1.1% | 29.2 | weak | ema_trend=22.5, macd_system=13.0, rsi_regime=18.0, bollinger=15.0, volume_obv=20.0, adx_stochastic=37.0, pattern_reco... |
| 77 | ORCL | Technology | August 2025 | BUY | down | -10.9% | 80.0 | strong | ema_trend=100.0, macd_system=57.0, rsi_regime=69.0, bollinger=79.0, volume_obv=80.0, adx_stochastic=73.0, pattern_rec... |
| 78 | ORCL | Technology | October 2025 | BUY | down | -8.5% | 59.5 | mixed_positive | ema_trend=85.0, macd_system=37.0, rsi_regime=62.0, bollinger=35.0, volume_obv=20.0, adx_stochastic=58.0, pattern_reco... |
| 79 | ORCL | Technology | January 2026 | BUY | down | -15.3% | 55.8 | mixed_positive | ema_trend=22.5, macd_system=56.0, rsi_regime=71.0, bollinger=46.0, volume_obv=65.0, adx_stochastic=52.0, pattern_reco... |
| 80 | TSLA | Technology | June 2025 | BUY | down | -6.6% | 69.2 | good | ema_trend=85.0, macd_system=54.0, rsi_regime=62.0, bollinger=59.0, volume_obv=65.0, adx_stochastic=51.0, pattern_reco... |
| 81 | TSLA | Technology | October 2025 | BUY | down | -1.0% | 76.6 | strong | ema_trend=100.0, macd_system=67.0, rsi_regime=62.0, bollinger=59.0, volume_obv=65.0, adx_stochastic=73.0, pattern_rec... |
| 82 | TSLA | Technology | November 2025 | BUY | down | -5.8% | 75.9 | strong | ema_trend=100.0, macd_system=57.0, rsi_regime=69.0, bollinger=80.0, volume_obv=65.0, adx_stochastic=37.0, pattern_rec... |
| 83 | TSLA | Technology | January 2026 | BUY | down | -4.3% | 52.2 | mixed_positive | ema_trend=85.0, macd_system=37.0, rsi_regime=38.0, bollinger=25.0, volume_obv=20.0, adx_stochastic=37.0, pattern_reco... |

### Top Misclassified Tickers

| Ticker | Sector | Misclassifications | FP | FN | Avg Return on Misclass |
|--------|--------|--------------------|----|----|-----------------------|
| OXY | Energy | 7 | 3 | 4 | -2.4% |
| AAPL | Technology | 6 | 5 | 1 | -2.5% |
| CRM | Technology | 6 | 5 | 1 | -5.2% |
| CVX | Energy | 5 | 4 | 1 | -3.7% |
| SLB | Energy | 5 | 2 | 3 | -0.8% |
| AMZN | Technology | 5 | 5 | 0 | -4.4% |
| MSFT | Technology | 5 | 4 | 1 | -3.3% |
| COP | Energy | 4 | 3 | 1 | -4.2% |
| EOG | Energy | 4 | 3 | 1 | -2.8% |
| HAL | Energy | 4 | 2 | 2 | +2.3% |
| VLO | Energy | 4 | 3 | 1 | -4.7% |
| META | Technology | 4 | 4 | 0 | -8.4% |
| NVDA | Technology | 4 | 3 | 1 | -5.3% |
| ORCL | Technology | 4 | 3 | 1 | -8.4% |
| TSLA | Technology | 4 | 4 | 0 | -4.4% |
