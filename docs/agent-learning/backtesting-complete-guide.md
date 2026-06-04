# Complete Backtesting & Model Evaluation Guide

**Author:** AI Agent (Claude Sonnet 4.5)  
**Date:** April 25, 2026  
**Purpose:** Comprehensive documentation of backtesting setup for model evaluation

---

## Table of Contents

1. [Overview](#overview)
2. [Critical Understanding: Two Modes](#critical-understanding-two-modes)
3. [Pure Prediction Mode (For Model Evaluation)](#pure-prediction-mode)
4. [Backtest Mode (For Trade Simulation)](#backtest-mode)
5. [Data Integrity Guarantees](#data-integrity-guarantees)
6. [Running Pure Predictions](#running-pure-predictions)
7. [Output Formats](#output-formats)
8. [Model Evaluation Workflow](#model-evaluation-workflow)
9. [Scripts Reference](#scripts-reference)
10. [Common Pitfalls & Solutions](#common-pitfalls--solutions)

---

## Overview

### Purpose

This system enables **model evaluation** by generating predictions on historical data without forward-looking bias. The goal is to test how accurate the orchestrator agent (combining technical and fundamental analysis) predicts stock movements.

### Key Principle: Temporal Integrity

```
Cutoff Date: 2025-09-30
─────────────────────────────────────────────
    PAST DATA ONLY          │   FUTURE DATA
    (Used for prediction)   │   (Never used for prediction)
                            │
✅ All data ≤ 2025-09-30    │ ❌ Data after 2025-09-30
✅ Pattern detection        │    NOT used for prediction
✅ Technical indicators     │    
✅ Entry price estimation   │ ✅ Used ONLY by YOU later
✅ Confidence scoring       │    to evaluate accuracy
                            │
← PREDICTION GENERATED →    │ ← YOUR EVALUATION →
```

**The system generates predictions. YOU evaluate accuracy by comparing to what actually happened.**

---

## Critical Understanding: Two Modes

### ⚠️ IMPORTANT: Know Which Mode You Need

There are **TWO completely different** systems for working with historical data:

| Aspect | Pure Prediction Mode | Backtest Mode |
|--------|---------------------|---------------|
| **Purpose** | Model evaluation | Trade simulation |
| **Script** | `run_pure_prediction.py` | `run_backtest_excel.py` |
| **Looks at future data?** | ❌ NO (never) | ❌ YES (for outcomes) |
| **Outputs outcomes?** | No | Yes (HIT_TARGET, HIT_STOP) |
| **Use for accuracy testing?** | ✅ YES | ❌ NO (biased) |
| **Use for strategy testing?** | ❌ NO | ✅ YES |
| **Data leakage?** | None | Intentional (for simulation) |

### When to Use Each Mode

**Use Pure Prediction Mode when:**
- Testing model accuracy
- Evaluating confidence calibration
- Comparing performance across time periods
- Academic/research purposes
- You want to evaluate "if I had used this model, would it have worked?"

**Use Backtest Mode when:**
- Testing trade execution strategies
- Optimizing position sizing
- Calculating risk-adjusted returns
- Simulating portfolio performance
- You want to know "if I had taken these trades, what would have happened?"

---

## Pure Prediction Mode

### What It Does

1. ✅ Loads all historical data up to cutoff date
2. ✅ Runs orchestrator agent (technical + fundamental fusion)
3. ✅ Generates prediction: BUY/HOLD/AVOID
4. ✅ Calculates confidence score (0-100)
5. ✅ Estimates entry price, target, stop loss
6. ❌ **NEVER** looks at data after cutoff date
7. ❌ **NEVER** calculates if prediction was correct

### Code Evidence: No Forward-Looking

**File:** `scripts/run_pure_prediction.py`

The pure prediction script:
- Calls `orchestrator.service.predict(ticker, as_of_date=cutoff_str)`
- Does NOT call `_simulate_trade()`
- Does NOT pass `target_days` parameter
- Does NOT look forward to calculate outcomes

**Key function:**
```python
def _predict_one_pure(ticker, sector, cutoff_str, ...):
    """Generate PURE PREDICTION - NO forward-looking"""
    
    # Uses ONLY data ≤ cutoff_date
    result = predict(ticker=ticker, as_of_date=cutoff_str)
    
    # Extract prediction components
    signal = "BUY" if sentiment == "bullish" else "HOLD"
    confidence = result.get("confidence_score", 0)
    
    # NO outcome calculation - just store prediction
    return prediction_row
```

### Running Pure Predictions

#### Single Date

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --date 2025-09-30 \
  --tickers-per-sector 9 \
  --workers 4
```

**Output:** `data/output/predictions/2025-09-30/predictions.json`

#### All Months of 2025

```bash
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

**Generates 12 cutoff dates:**
- 2025-01-31, 2025-02-28, 2025-03-31, 2025-04-30, 2025-05-31, 2025-06-30
- 2025-07-31, 2025-08-31, 2025-09-30, 2025-10-31, 2025-11-30, 2025-12-31

**Total records:** ~1,080 (12 months × 90 tickers)

**Time:** ~20-30 minutes

**Output:** `data/output/predictions/2025_monthly/predictions.json`

#### Custom Date Range

```bash
# Q3 2025 only (weekly intervals)
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --start 2025-07-01 \
  --end 2025-09-30 \
  --interval weekly \
  --tickers-per-sector 9 \
  --workers 4
```

---

## Backtest Mode

### What It Does

1. ✅ Loads all historical data up to cutoff date
2. ✅ Runs orchestrator agent
3. ✅ Generates prediction
4. ❌ **THEN looks forward** 20 days to see if target/stop hit
5. ❌ Calculates outcome: HIT_TARGET, HIT_STOP, EXPIRED
6. ❌ Calculates P&L %

### Code Evidence: Forward-Looking

**File:** `agents/technical/predictor.py` (Lines 602-611)

```python
# ── Walk-forward simulation ───────────────────────────────────────────
exit_date, exit_price, exit_outcome, bars_simulated = _simulate_trade(
    bars          = bars,
    entry_bar_idx = entry_bar_idx,
    entry_date    = entry_date,
    entry_price   = entry_price,
    stop_price    = stop_price,
    target_price  = target_price,
    max_bars      = target_days,  # ← LOOKS 20 DAYS FORWARD
)
```

**Line 492-493 comment:**
```python
# bars may include forward bars (after cutoff) for walk-forward simulation.
```

### When to Use Backtest Mode

✅ Use backtest mode for:
- Testing trade execution timing
- Optimizing stop loss placement
- Position sizing strategies
- Risk management rules
- Portfolio simulation

❌ Do NOT use backtest mode for:
- Model accuracy evaluation
- Confidence calibration testing
- Comparing model versions

### Running Backtest Mode

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_backtest_excel.py \
  --date 2025-09-30 \
  --tickers-per-sector 9 \
  --workers 4 \
  --target-days 20
```

**Output:** `data/output/backtests/2026-04-25/2026-04-25.xlsx`

---

## Data Integrity Guarantees

### Pure Prediction Mode Guarantees

#### 1. Data Boundary Enforcement

**Cutoff date strictly enforced:**
```python
# agents/orchestrator/service.py
result = predict(ticker=ticker, as_of_date=cutoff_str)
#                                ^^^^^^^^^^^^^^^^
# All data fetched is bounded by this date
```

**Data client respects cutoff:**
```python
# agents/technical/data_client.py
bars = client.fetch_ohlcv(
    ticker=ticker,
    start_date=start_date,
    end_date=cutoff_date,  # ← Hard stop here
)
```

#### 2. Pattern Detection

**Uses ONLY historical bars:**
- Pattern start date < cutoff date
- Pattern end date ≤ cutoff date
- Breakout date ≤ cutoff date
- No future bars accessed

#### 3. Technical Indicators

**Calculated from historical data only:**
```python
# agents/technical/indicators.py
rsi_14 = calculate_rsi(bars, period=14)
#                      ^^^^
# bars array contains ONLY data ≤ cutoff_date
```

**Indicators computed:**
- ATR (Average True Range)
- ADX (Average Directional Index)
- RSI (Relative Strength Index)
- Moving averages
- Volume metrics

All use data ≤ cutoff date only.

#### 4. Entry Price Estimation

**From last available bar:**
```python
# predictor.py line 568
entry_price = round(bars[-1].close, 2)
#                   ^^^^^^^^^
# Last bar in array = cutoff date bar
```

#### 5. Entry Conviction

**Derived from staleness check (no future data):**
```python
def _entry_conviction(breakout_date, current_date, current_price, breakout_price):
    days_since_breakout = _count_trading_days_between(breakout_date, current_date)
    extension_pct = ((current_price - breakout_price) / breakout_price) * 100
    
    if days_since_breakout <= 5 and extension_pct < 3:
        return "IMMEDIATE"
    elif extension_pct <= 5 or (days_since_breakout <= 3):
        return "RETEST_ENTRY"
    else:
        return "WAIT_FOR_RETEST"
```

All variables computed from data ≤ cutoff date.

### What Pure Prediction Mode Does NOT Do

❌ **NEVER looks at future bars:**
- No `_simulate_trade()` call
- No forward bar access
- No outcome calculation

❌ **NEVER calculates:**
- Exit date
- Exit price
- Whether target was hit
- Whether stop was hit
- Actual P&L

❌ **NEVER uses:**
- `target_days` parameter for simulation
- Bars after cutoff date
- Future price data

---

## Output Formats

### Pure Prediction Output (NO OUTCOMES)

```json
{
  "Ticker": "AAPL",
  "Sector": "Information Technology",
  "Cutoff Date": "2025-09-30",
  "Signal": "BUY",
  "Confidence Score": 70.7,
  "Tech Score": 72.0,
  "Fund Score": 68.0,
  "Pattern Name": "Cup & Handle",
  "Pattern Start": "2025-08-15",
  "Pattern End": "2025-09-28",
  "Breakout Date": "2025-09-28",
  "Entry Conviction": "RETEST_ENTRY",
  "Price Extension %": 2.3,
  "Entry Price (Est.)": 227.80,
  "Retest Zone Low": 223.00,
  "Retest Zone High": 225.50,
  "Target Price": 245.00,
  "Stop Loss": 220.00,
  "R/R Ratio": 2.2,
  "ATR": 3.85,
  "ADX": 28.5,
  "RSI": 58.2,
  "Est. Days to Target": 15,
  "No Trade Reason": "",
  "Prediction Timestamp": "2026-04-25T20:15:30"
}
```

**Note: NO outcome fields present.**

### Backtest Output (WITH OUTCOMES)

```json
{
  "Ticker": "AAPL",
  "Cutoff Date": "2025-09-30",
  "Signal": "BUY",
  "Confidence Score": 70.7,
  "Entry Price (Est.)": 227.80,
  "Target Price": 245.00,
  "Stop Loss": 220.00,
  "Outcome": "HIT_TARGET",
  "Exit Date": "2025-10-15",
  "Exit Price": 245.10,
  "Gross P&L %": 7.6,
  "Net P&L %": 7.1,
  "Run Timestamp": "2026-04-25T19:52:28"
}
```

**Note: Outcome fields present (forward-looking).**

### Field Definitions

#### Core Fields (Both Modes)

| Field | Type | Description |
|-------|------|-------------|
| `Ticker` | string | Stock symbol |
| `Sector` | string | GICS sector classification |
| `Cutoff Date` | date | Analysis date (YYYY-MM-DD) |
| `Signal` | enum | **BUY**, **HOLD**, **AVOID** |
| `Confidence Score` | float | Overall score (0-100) |
| `Tech Score` | float | Technical analysis score (0-100) |
| `Fund Score` | float | Fundamental analysis score (0-100) |

#### Pattern Fields

| Field | Type | Description |
|-------|------|-------------|
| `Pattern Name` | string | Cup & Handle, Bull Flag, etc. |
| `Pattern Start` | date | Pattern formation start |
| `Pattern End` | date | Pattern completion (≤ cutoff) |
| `Breakout Date` | date | True breakout date (≤ cutoff) |
| `Price Extension %` | float | % above breakout price at cutoff |

#### Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `Entry Conviction` | enum | IMMEDIATE, RETEST_ENTRY, WAIT_FOR_RETEST |
| `Entry Price (Est.)` | float | Estimated entry (close at cutoff) |
| `Retest Zone Low` | float | Lower retest zone bound |
| `Retest Zone High` | float | Upper retest zone (≈ breakout price) |

#### Target Fields

| Field | Type | Description |
|-------|------|-------------|
| `Target Price` | float | Price target from pattern |
| `Stop Loss` | float | Stop loss (entry - 2×ATR) |
| `R/R Ratio` | float | Reward/Risk ratio |
| `Est. Days to Target` | int | Estimated days to hit target |

#### Indicator Fields

| Field | Type | Description |
|-------|------|-------------|
| `ATR` | float | Average True Range (14-period) |
| `ADX` | float | Average Directional Index |
| `RSI` | float | Relative Strength Index (14-period) |

#### Outcome Fields (Backtest Mode Only)

| Field | Type | Description |
|-------|------|-------------|
| `Outcome` | enum | HIT_TARGET, HIT_STOP, EXPIRED, OPEN, SKIP |
| `Exit Date` | date | Actual exit date |
| `Exit Price` | float | Actual exit price |
| `Gross P&L %` | float | Gross profit/loss % |
| `Net P&L %` | float | Net P/L after costs |

---

## Model Evaluation Workflow

### Step 1: Generate Pure Predictions

```bash
# Generate predictions for all of 2025 (monthly)
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

**Output:** `data/output/predictions/2025_monthly/predictions.json`

**Contains:** ~1,080 predictions (12 months × 90 tickers)

### Step 2: Load Predictions

```python
import json
import pandas as pd

# Load all predictions
with open('data/output/predictions/2025_monthly/predictions.json') as f:
    predictions = json.load(f)

df = pd.DataFrame(predictions)

# Filter for BUY signals only
buy_signals = df[df['Signal'] == 'BUY']
print(f"Total BUY signals: {len(buy_signals)}")

# Group by cutoff date
by_month = buy_signals.groupby('Cutoff Date').size()
print("\nBUY signals per month:")
print(by_month)
```

### Step 3: Fetch Actual Data (Your Responsibility)

```python
import yfinance as yf
from datetime import datetime, timedelta

def evaluate_prediction(pred):
    """
    Evaluate a single prediction by fetching actual data
    AFTER the cutoff date.
    """
    ticker = pred['Ticker']
    cutoff_date = datetime.fromisoformat(pred['Cutoff Date'])
    entry_price = pred['Entry Price (Est.)']
    target_price = pred['Target Price']
    stop_price = pred['Stop Loss']
    
    # Fetch actual data AFTER cutoff (this is YOUR code, not mine)
    start_date = cutoff_date + timedelta(days=1)
    end_date = cutoff_date + timedelta(days=30)  # ~20 trading days
    
    try:
        actual_data = yf.download(
            ticker, 
            start=start_date, 
            end=end_date, 
            progress=False
        )
        
        if actual_data.empty:
            return {'outcome': 'NO_DATA', 'days_to_outcome': None}
        
        # Check if target or stop hit
        hit_target_mask = actual_data['High'] >= target_price
        hit_stop_mask = actual_data['Low'] <= stop_price
        
        if hit_target_mask.any() and not hit_stop_mask.any():
            target_date = actual_data[hit_target_mask].index[0]
            days = (target_date - cutoff_date).days
            return {'outcome': 'WIN', 'days_to_outcome': days}
        
        elif hit_stop_mask.any():
            stop_date = actual_data[hit_stop_mask].index[0]
            days = (stop_date - cutoff_date).days
            return {'outcome': 'LOSS', 'days_to_outcome': days}
        
        else:
            return {'outcome': 'EXPIRED', 'days_to_outcome': None}
    
    except Exception as e:
        return {'outcome': 'ERROR', 'error': str(e)}

# Evaluate all BUY signals
results = []
for idx, pred in buy_signals.iterrows():
    evaluation = evaluate_prediction(pred)
    results.append({
        'ticker': pred['Ticker'],
        'cutoff_date': pred['Cutoff Date'],
        'predicted_signal': pred['Signal'],
        'confidence': pred['Confidence Score'],
        'entry_conviction': pred['Entry Conviction'],
        'actual_outcome': evaluation['outcome'],
        'days_to_outcome': evaluation.get('days_to_outcome')
    })

results_df = pd.DataFrame(results)
```

### Step 4: Calculate Accuracy Metrics

```python
# Overall win rate
wins = (results_df['actual_outcome'] == 'WIN').sum()
losses = (results_df['actual_outcome'] == 'LOSS').sum()
win_rate = wins / (wins + losses) * 100

print(f"\n{'='*60}")
print(f"MODEL EVALUATION RESULTS")
print(f"{'='*60}")
print(f"Total predictions evaluated: {len(results_df)}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Expired: {(results_df['actual_outcome'] == 'EXPIRED').sum()}")
print(f"Win Rate: {win_rate:.1f}%")

# Win rate by confidence band
print(f"\n{'='*60}")
print(f"WIN RATE BY CONFIDENCE LEVEL")
print(f"{'='*60}")

for min_conf in [60, 65, 70, 75, 80]:
    high_conf = results_df[results_df['confidence'] >= min_conf]
    if len(high_conf) == 0:
        continue
    hc_wins = (high_conf['actual_outcome'] == 'WIN').sum()
    hc_losses = (high_conf['actual_outcome'] == 'LOSS').sum()
    if (hc_wins + hc_losses) > 0:
        hc_wr = hc_wins / (hc_wins + hc_losses) * 100
        print(f"Confidence >= {min_conf}: {len(high_conf):3} trades | Win Rate: {hc_wr:5.1f}%")

# Win rate by entry conviction
print(f"\n{'='*60}")
print(f"WIN RATE BY ENTRY CONVICTION")
print(f"{'='*60}")

for conviction in ['IMMEDIATE', 'RETEST_ENTRY', 'WAIT_FOR_RETEST']:
    conv_df = results_df[results_df['entry_conviction'] == conviction]
    if len(conv_df) == 0:
        continue
    conv_wins = (conv_df['actual_outcome'] == 'WIN').sum()
    conv_losses = (conv_df['actual_outcome'] == 'LOSS').sum()
    if (conv_wins + conv_losses) > 0:
        conv_wr = conv_wins / (conv_wins + conv_losses) * 100
        print(f"{conviction:20}: {len(conv_df):3} trades | Win Rate: {conv_wr:5.1f}%")

# Average days to outcome
print(f"\n{'='*60}")
print(f"TIME TO OUTCOME")
print(f"{'='*60}")

wins_with_days = results_df[
    (results_df['actual_outcome'] == 'WIN') & 
    (results_df['days_to_outcome'].notna())
]
if len(wins_with_days) > 0:
    avg_days_to_win = wins_with_days['days_to_outcome'].mean()
    print(f"Average days to target: {avg_days_to_win:.1f}")

losses_with_days = results_df[
    (results_df['actual_outcome'] == 'LOSS') & 
    (results_df['days_to_outcome'].notna())
]
if len(losses_with_days) > 0:
    avg_days_to_loss = losses_with_days['days_to_outcome'].mean()
    print(f"Average days to stop: {avg_days_to_loss:.1f}")
```

### Step 5: Export Results

```python
# Save evaluation results
results_df.to_csv('model_evaluation_2025.csv', index=False)
results_df.to_json('model_evaluation_2025.json', orient='records', indent=2)

print(f"\nResults saved to:")
print(f"  - model_evaluation_2025.csv")
print(f"  - model_evaluation_2025.json")
```

---

## Scripts Reference

### Pure Prediction Script

**File:** `scripts/run_pure_prediction.py`

**Purpose:** Generate predictions without forward-looking bias

**Key Functions:**
- `_predict_one_pure()` - Generate single prediction (NO outcome calculation)
- `_select_tickers()` - Select tickers from halal universe
- `generate_cutoff_dates()` - Generate cutoff dates for interval
- `main()` - Main execution loop

**Parameters:**
```bash
--date                  Single cutoff date (YYYY-MM-DD)
--year                  Full year to process (e.g., 2025)
--start                 Start date for custom range
--end                   End date for custom range
--interval              weekly, biweekly, monthly (default: monthly)
--workers               Thread pool size (default: 4)
--tickers-per-sector    Tickers per sector (default: 9)
--sector                Filter specific sector
```

**Output:**
- `predictions.xlsx` - Excel workbook
- `predictions.json` - JSON array
- `run_log.txt` - Execution log

### Backtest Script

**File:** `scripts/run_backtest_excel.py`

**Purpose:** Trade simulation with outcome calculation

**Key Functions:**
- `_predict_one()` - Run prediction + outcome simulation
- `_write_row()` - Thread-safe Excel write
- `main()` - Main execution loop

**Parameters:**
```bash
--date              Cutoff date (YYYY-MM-DD)
--workers           Thread pool size (default: 4)
--target-days       Trade window in days (default: 20)
--tickers-per-sector  Tickers per sector (default: 9)
--sector            Filter specific sector
```

**Output:**
- `<date>.xlsx` - Excel workbook with outcomes
- `<date>.json` - JSON with outcomes
- `run_log.txt` - Execution log

### Export to Dashboard Script

**File:** `scripts/export_to_dashboard.py`

**Purpose:** Transform backtest/prediction JSON to dashboard format

**Transforms:**
- Backtest JSON → Dashboard prediction format
- Sector summaries
- High confidence setups
- Signal distributions

**Usage:**
```bash
python3 scripts/export_to_dashboard.py
```

**Output:**
- `backtest-dashboard/app/data/prediction-data.json`
- `backtest-dashboard/app/data/dashboard-data.json`

---

## Common Pitfalls & Solutions

### Pitfall 1: Using Backtest Mode for Accuracy Testing

❌ **Problem:**
```python
# WRONG: Using backtest mode for model evaluation
backtest_results = run_backtest(date="2025-09-30", target_days=20)
win_rate = calculate_win_rate(backtest_results)
# ↑ This is BIASED because it looks forward!
```

✅ **Solution:**
```python
# CORRECT: Use pure prediction mode
predictions = run_pure_prediction(date="2025-09-30")
# Then YOU evaluate by fetching actual data separately
actual_results = fetch_actual_data_after_cutoff(predictions)
win_rate = calculate_win_rate(predictions, actual_results)
```

### Pitfall 2: Confusing Cutoff Date with Run Date

❌ **Problem:**
```
Running backtest on 2026-04-25 for cutoff date 2025-09-30
Output folder: data/output/backtests/2026-04-25/
```

**Confusion:** "Why is the folder named 2026-04-25 when I'm testing 2025-09-30?"

✅ **Clarification:**
- **Cutoff date (2025-09-30):** The date being analyzed (historical)
- **Run date (2026-04-25):** Today, when you're running the script
- **Folder naming:** Uses run date to group multiple cutoff dates together
- **Data used:** ONLY up to cutoff date (2025-09-30), NOT run date

### Pitfall 3: Not Waiting for API Rate Limits

❌ **Problem:**
```bash
# Running with too many workers
python3 scripts/run_pure_prediction.py --workers 16
# ↑ May hit Polygon API rate limits
```

✅ **Solution:**
```bash
# Use recommended worker count
python3 scripts/run_pure_prediction.py --workers 4
# Optimal: 3-6 workers to avoid rate limits
```

### Pitfall 4: Evaluating with Insufficient Data Window

❌ **Problem:**
```python
# Only checking 5 days after cutoff
end_date = cutoff_date + timedelta(days=5)
# ↑ May miss targets that take 10-15 days to hit
```

✅ **Solution:**
```python
# Use appropriate window (20-30 trading days ≈ 30-45 calendar days)
end_date = cutoff_date + timedelta(days=45)
# Matches the Est. Days to Target field
```

### Pitfall 5: Not Filtering by Signal Type

❌ **Problem:**
```python
# Evaluating ALL predictions (including HOLD/AVOID)
all_predictions = load_predictions()
win_rate = evaluate_all(all_predictions)
# ↑ Doesn't make sense - HOLD/AVOID are not trades
```

✅ **Solution:**
```python
# Only evaluate BUY signals
buy_signals = [p for p in predictions if p['Signal'] == 'BUY']
win_rate = evaluate_trades(buy_signals)
# Only BUY signals represent actual trade recommendations
```

### Pitfall 6: Ignoring Entry Conviction

❌ **Problem:**
```python
# Treating all BUY signals the same
all_buys = filter_buys(predictions)
# ↑ Mixing IMMEDIATE, RETEST_ENTRY, WAIT_FOR_RETEST
```

✅ **Solution:**
```python
# Separate by entry conviction
immediate = [p for p in predictions if p['Entry Conviction'] == 'IMMEDIATE']
retest = [p for p in predictions if p['Entry Conviction'] == 'RETEST_ENTRY']
wait = [p for p in predictions if p['Entry Conviction'] == 'WAIT_FOR_RETEST']

# Evaluate each separately
immediate_wr = evaluate(immediate)
retest_wr = evaluate(retest)
wait_wr = evaluate(wait)
```

### Pitfall 7: Not Accounting for Errors

❌ **Problem:**
```python
# Not filtering ERROR records
all_results = load_predictions()
win_rate = calculate_wr(all_results)
# ↑ ERROR records pollute the dataset
```

✅ **Solution:**
```python
# Filter out errors
valid = [p for p in predictions if p['Signal'] != 'ERROR']
buy_signals = [p for p in valid if p['Signal'] == 'BUY']
win_rate = calculate_wr(buy_signals)
```

---

## Quick Reference Commands

### Generate Single Month Prediction

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --date 2025-09-30 \
  --tickers-per-sector 9 \
  --workers 4
```

### Generate Full Year (Monthly)

```bash
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

### Generate Quarterly (Weekly Intervals)

```bash
# Q1 2025
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --start 2025-01-01 \
  --end 2025-03-31 \
  --interval weekly \
  --workers 4

# Q2 2025
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --start 2025-04-01 \
  --end 2025-06-30 \
  --interval weekly \
  --workers 4
```

### Export to Dashboard

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

python3 scripts/export_to_dashboard.py
```

---

## Summary

### Key Takeaways

1. **Two Modes Exist:**
   - Pure Prediction Mode: For model evaluation (NO forward-looking)
   - Backtest Mode: For trade simulation (intentional forward-looking)

2. **Data Integrity:**
   - Pure prediction uses ONLY data ≤ cutoff date
   - No forward simulation
   - No outcome calculation

3. **Your Responsibility:**
   - Generate predictions using pure prediction mode
   - Fetch actual data AFTER cutoff date separately
   - Calculate accuracy yourself by comparing predictions to actual results

4. **Model Evaluation:**
   - Run predictions for multiple time periods (monthly/weekly)
   - Evaluate win rates by confidence level
   - Test performance across different market conditions
   - Validate confidence calibration

5. **Best Practices:**
   - Use 3-6 workers to avoid API rate limits
   - Filter by signal type (BUY only for trades)
   - Separate by entry conviction
   - Remove ERROR records
   - Use appropriate evaluation window (20-30 trading days)

---

## Questions & Troubleshooting

### Q: Why two different modes?

**A:** Different purposes require different approaches:
- **Model evaluation** requires NO forward-looking (pure prediction mode)
- **Trade simulation** requires looking forward to see outcomes (backtest mode)

### Q: Can I trust the predictions are not using future data?

**A:** Yes. Code evidence:
- Pure prediction script does NOT call `_simulate_trade()`
- Does NOT pass `target_days` parameter
- Does NOT access bars after cutoff date
- Documented data boundary enforcement

### Q: How do I know which mode I'm using?

**A:** Check the script name:
- `run_pure_prediction.py` = Pure prediction mode (NO forward-looking)
- `run_backtest_excel.py` = Backtest mode (forward-looking for outcomes)

### Q: What if I get API rate limit errors?

**A:** Reduce workers:
```bash
--workers 3  # or even 2
```

Or add delays between batches (modify script).

### Q: How long does full year take?

**A:**
- Monthly (12 dates): ~20-30 minutes
- Weekly (52 dates): ~1.5-2 hours
- Daily (252 dates): ~8-10 hours

### Q: Can I run multiple cutoff dates in parallel?

**A:** No, run them sequentially to avoid API conflicts. The script handles parallelization at the ticker level, not the date level.

---

**End of Complete Backtesting Guide**

Last Updated: April 25, 2026
