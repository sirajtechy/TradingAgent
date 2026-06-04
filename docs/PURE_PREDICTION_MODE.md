# Pure Prediction Mode vs Backtest Mode

## ⚠️ CRITICAL DIFFERENCE

There are TWO different modes for running predictions on historical data:

### 1. **Backtest Mode** (Forward-Looking) ❌ Not for Model Evaluation

**Script:** `run_backtest_excel.py`

**What it does:**
- Uses data ≤ cutoff date for prediction
- **THEN looks forward** to see if trade hits target/stop
- Calculates outcomes: HIT_TARGET, HIT_STOP, EXPIRED
- **PURPOSE:** Trade strategy simulation

**Code evidence:**
```python
# agents/technical/predictor.py Line 602-611
exit_date, exit_price, exit_outcome, bars_simulated = _simulate_trade(
    bars = bars,
    max_bars = target_days,  # ← Looks 20 days FORWARD
)
```

**When to use:** Trade strategy development, position sizing, risk management

**NOT for:** Model evaluation, accuracy testing, confidence calibration

---

### 2. **Pure Prediction Mode** (NO Forward-Looking) ✅ For Model Evaluation

**Script:** `run_pure_prediction.py`

**What it does:**
- Uses data ≤ cutoff date for prediction
- Outputs: Signal (BUY/HOLD/AVOID), confidence, targets
- **NEVER looks forward**
- **NO outcomes** in output
- **PURPOSE:** Model evaluation & validation

**When to use:** 
- Evaluating model accuracy
- Testing confidence calibration
- Comparing predictions across time periods
- Academic/research purposes

---

## 🎯 Your Use Case: Model Evaluation

Based on your requirements:

> "I wanted to do the outcome calculation, and all I wanted is the prediction evaluation that you have done from the historical data."

> "for the outcome calculation you won't be seeing the future candles or anything of that sort"

> "not to crawl the data which is a far-away candle, so it will pollute the data by seeing the future"

**You want:** **Pure Prediction Mode**

---

## Running Pure Predictions

### Single Date (September 2025)

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --date 2025-09-30 \
  --tickers-per-sector 9 \
  --workers 4
```

### All Months of 2025 (Monthly Predictions)

```bash
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

This generates predictions for:
- 2025-01-31
- 2025-02-28
- 2025-03-31
- 2025-04-30
- 2025-05-31
- 2025-06-30
- 2025-07-31
- 2025-08-31
- 2025-09-30
- 2025-10-31
- 2025-11-30
- 2025-12-31

**~1,080 prediction records** (12 months × 90 tickers)

---

## Output Format: Pure Predictions

### JSON Structure (NO OUTCOMES)

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

**Key differences from backtest mode:**
- ❌ NO "Outcome" field
- ❌ NO "Exit Date"
- ❌ NO "Exit Price"
- ❌ NO "Gross P&L %"
- ❌ NO "Net P&L %"

**What you GET:**
- ✅ Prediction made at cutoff date
- ✅ Signal confidence
- ✅ Predicted targets
- ✅ Entry conviction level

---

## How to Evaluate Model Accuracy (Your Responsibility)

### Step 1: Generate Predictions

```bash
python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

Output: `data/output/predictions/2025_monthly/predictions.json`

### Step 2: Load Actual Price Data (Separately)

You load actual price data for the period AFTER each cutoff date:

```python
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Load predictions
with open('data/output/predictions/2025_monthly/predictions.json') as f:
    predictions = json.load(f)

# For each prediction, load actual data AFTER cutoff date
results = []
for pred in predictions:
    if pred['Signal'] != 'BUY':
        continue
        
    ticker = pred['Ticker']
    cutoff_date = datetime.fromisoformat(pred['Cutoff Date'])
    entry_price = pred['Entry Price (Est.)']
    target_price = pred['Target Price']
    stop_price = pred['Stop Loss']
    
    # Load actual data AFTER cutoff (this is YOUR responsibility)
    start_date = cutoff_date + timedelta(days=1)
    end_date = cutoff_date + timedelta(days=30)  # 20 trading days ≈ 30 calendar
    
    actual_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    # Check if target or stop hit
    hit_target = (actual_data['High'] >= target_price).any()
    hit_stop = (actual_data['Low'] <= stop_price).any()
    
    # Determine outcome
    if hit_target and not hit_stop:
        outcome = 'WIN'
    elif hit_stop:
        outcome = 'LOSS'
    else:
        outcome = 'EXPIRED'
    
    results.append({
        'ticker': ticker,
        'cutoff_date': pred['Cutoff Date'],
        'predicted_signal': pred['Signal'],
        'confidence': pred['Confidence Score'],
        'actual_outcome': outcome
    })

# Calculate accuracy
df = pd.DataFrame(results)
win_rate = (df['actual_outcome'] == 'WIN').sum() / len(df) * 100
print(f"Win Rate: {win_rate:.1f}%")

# Accuracy by confidence band
high_conf = df[df['confidence'] >= 70]
print(f"High Confidence Win Rate: {(high_conf['actual_outcome'] == 'WIN').sum() / len(high_conf) * 100:.1f}%")
```

---

## Comparison Table

| Feature | Backtest Mode | Pure Prediction Mode |
|---------|---------------|----------------------|
| **Script** | `run_backtest_excel.py` | `run_pure_prediction.py` |
| **Uses data ≤ cutoff** | ✅ Yes | ✅ Yes |
| **Looks at future data** | ❌ YES (for outcomes) | ✅ NO (never) |
| **Outputs outcomes** | Yes (HIT_TARGET, HIT_STOP) | No |
| **Purpose** | Trade simulation | Model evaluation |
| **Suitable for** | Strategy testing | Accuracy testing |
| **Data leakage** | Yes (intentional) | No (prevented) |

---

## ✅ Confirmation: Pure Prediction Mode

I have created `run_pure_prediction.py` which:

1. ✅ **Uses ONLY data before cutoff date**
   - No forward-looking simulation
   - No `_simulate_trade()` calls
   - No `target_days` lookforward

2. ✅ **Outputs predictions only**
   - Signal (BUY/HOLD/AVOID)
   - Confidence scores
   - Predicted targets/stops
   - Entry conviction

3. ✅ **NO outcomes calculated**
   - You evaluate accuracy later
   - Compare predictions to actual results
   - Calculate win rates yourself

4. ✅ **Maximum historical data consumption**
   - Uses all available data ≤ cutoff
   - Patterns detected from full history
   - Indicators calculated from all available bars

---

## Your Next Steps

### 1. Run Pure Predictions for 2025

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

# Monthly predictions for entire 2025
FMP_API_KEY=RZ8P7bENfukSirRglbdDQ30jIfjKsqSY python3 scripts/run_pure_prediction.py \
  --year 2025 \
  --interval monthly \
  --tickers-per-sector 9 \
  --workers 4
```

### 2. Evaluate Model Accuracy

Write your own evaluation script that:
- Loads the predictions JSON
- Fetches actual price data AFTER each cutoff date
- Calculates if predictions were correct
- Computes win rates, accuracy by confidence level, etc.

### 3. Test Different Time Periods

```bash
# Q1 2025
python3 scripts/run_pure_prediction.py --start 2025-01-01 --end 2025-03-31 --interval weekly

# Q2 2025
python3 scripts/run_pure_prediction.py --start 2025-04-01 --end 2025-06-30 --interval weekly

# Q3 2025
python3 scripts/run_pure_prediction.py --start 2025-07-01 --end 2025-09-30 --interval weekly

# Q4 2025
python3 scripts/run_pure_prediction.py --start 2025-10-01 --end 2025-12-31 --interval weekly
```

---

## I'm Ready for Your Challenge

You said:
> "challenge me that what you're doing is correct. If you're trying to get deviated, just let me know."

**My Answer:**

1. ✅ I found the forward-looking code in `predictor.py` line 602-611
2. ✅ I admitted the old `run_backtest_excel.py` DOES look at future data
3. ✅ I created NEW `run_pure_prediction.py` that NEVER looks forward
4. ✅ This is now correct for model evaluation

**The pure prediction mode:**
- Uses ONLY data ≤ cutoff date
- Never calls `_simulate_trade()`
- Never looks at future candles
- Outputs predictions without outcomes
- You evaluate accuracy separately

**Is this what you wanted?**
