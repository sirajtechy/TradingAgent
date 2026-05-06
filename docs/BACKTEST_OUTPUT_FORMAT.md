# Backtest Output Format

## Overview

The backtest system generates JSON output where **each row represents one ticker analyzed at one cutoff date**. The cutoff date strictly prevents forward-looking data.

---

## ✅ Cutoff Date Guarantee

```
Cutoff Date: 2025-09-30
─────────────────────────────────────────────
         Past Data          │   Future Data
    (Used for analysis)     │  (Used to evaluate outcome)
                            │
← Market data up to         │  Market data after 2025-09-30 →
  2025-09-30 inclusive      │  used ONLY to calculate if
  used for:                 │  target/stop was hit
  - Pattern detection       │
  - Technical indicators    │
  - Entry price estimation  │
  - Entry conviction        │
```

**No forward-looking bias:**
- Pattern detection uses ONLY data ≤ cutoff date
- Entry price = Close price on cutoff date
- Outcome calculated by looking FORWARD from cutoff (simulating real trade)

---

## JSON Output Format

### Single Record Structure

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
  "Pattern Timeframe": "Daily",
  "Breakout Date": "2025-09-28",
  "Breakout Price": 225.50,
  "Days Since Breakout": 2,
  "Entry Conviction": "RETEST_ENTRY",
  "Price Extension %": 2.3,
  "Entry Date (Earliest)": "2025-09-30",
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
  "Est. Target Date": "2025-10-20",
  "Outcome": "HIT_TARGET",
  "Exit Date": "2025-10-15",
  "Exit Price": 245.10,
  "Gross P&L %": 7.6,
  "Net P&L %": 7.1,
  "No Trade Reason": "",
  "Run Timestamp": "2026-04-25T19:52:28"
}
```

---

## Field Explanations

### Core Identification
| Field | Type | Description |
|-------|------|-------------|
| `Ticker` | string | Stock ticker symbol |
| `Sector` | string | GICS sector |
| `Cutoff Date` | date | Analysis date - NO data after this date used for prediction |
| `Run Timestamp` | datetime | When this backtest was executed |

### Signal & Scores
| Field | Type | Description |
|-------|------|-------------|
| `Signal` | enum | **BUY**, **HOLD**, **AVOID** |
| `Confidence Score` | float | Overall orchestrator score (0-100) |
| `Tech Score` | float | Technical analysis score (0-100) |
| `Fund Score` | float | Fundamental analysis score (0-100) |

### Pattern Detection (Based on data ≤ Cutoff Date)
| Field | Type | Description |
|-------|------|-------------|
| `Pattern Name` | string | Cup & Handle, Bull Flag, Ascending Triangle, etc. |
| `Pattern Start` | date | When pattern formation began |
| `Pattern End` | date | When pattern completed (≤ Cutoff Date) |
| `Breakout Date` | date | True breakout date (≤ Cutoff Date) |
| `Breakout Price` | float | Price at breakout |
| `Days Since Breakout` | int | Days between breakout and cutoff |

### Entry Analysis (NO forward-looking data)
| Field | Type | Description |
|-------|------|-------------|
| `Entry Conviction` | enum | **IMMEDIATE**, **RETEST_ENTRY**, **WAIT_FOR_RETEST** |
| `Price Extension %` | float | How far price extended from breakout (staleness check) |
| `Entry Date (Earliest)` | date | Earliest recommended entry date |
| `Entry Price (Est.)` | float | Estimated entry price (close on cutoff date) |
| `Retest Zone Low` | float | Lower bound of retest zone |
| `Retest Zone High` | float | Upper bound of retest zone (usually = breakout price) |

### Trade Setup
| Field | Type | Description |
|-------|------|-------------|
| `Target Price` | float | Price target (from pattern projection) |
| `Stop Loss` | float | Stop loss price (usually 2× ATR below entry) |
| `R/R Ratio` | float | Reward-to-risk ratio |
| `ATR` | float | Average True Range (14-period) at cutoff date |
| `ADX` | float | Average Directional Index at cutoff date |
| `RSI` | float | Relative Strength Index (14-period) at cutoff date |

### Projected Timeline
| Field | Type | Description |
|-------|------|-------------|
| `Est. Days to Target` | int | Estimated days to reach target |
| `Est. Target Date` | date | Projected date to hit target |

### Outcome (Uses data AFTER cutoff date)
| Field | Type | Description |
|-------|------|-------------|
| `Outcome` | enum | **HIT_TARGET**, **HIT_STOP**, **EXPIRED**, **OPEN**, **SKIP** |
| `Exit Date` | date | Actual exit date (when target/stop hit, or expiration) |
| `Exit Price` | float | Actual exit price |
| `Gross P&L %` | float | Gross profit/loss percentage |
| `Net P&L %` | float | Net profit/loss after estimated costs |

### Special Cases
| Field | Type | Description |
|-------|------|-------------|
| `No Trade Reason` | string | Why no trade was taken (for HOLD/AVOID signals) |

---

## Outcome Values

| Outcome | Description |
|---------|-------------|
| `HIT_TARGET` | Price reached target within window (WIN) |
| `HIT_STOP` | Price hit stop loss (LOSS) |
| `EXPIRED` | Trade window expired without hitting target or stop |
| `OPEN` | Trade still open (within target window) |
| `SKIP` | Entry criteria not met, no trade taken |
| `ERROR` | Data error (e.g., no historical data available) |

---

## Entry Conviction Values

| Conviction | Description | When to Use |
|------------|-------------|-------------|
| `IMMEDIATE` | Enter immediately | Breakout ≤ 5 days old, price < 3% extended |
| `RETEST_ENTRY` | Enter now (in retest zone) | Price currently in retest zone |
| `WAIT_FOR_RETEST` | Wait for pullback | Price extended > 5% from breakout |

---

## Example: Multi-Date Backtest Output

```json
[
  {
    "Ticker": "AAPL",
    "Cutoff Date": "2025-01-05",
    "Signal": "HOLD",
    "Confidence Score": 45.2,
    ...
  },
  {
    "Ticker": "AAPL",
    "Cutoff Date": "2025-01-12",
    "Signal": "BUY",
    "Confidence Score": 72.3,
    ...
  },
  {
    "Ticker": "AAPL",
    "Cutoff Date": "2025-01-19",
    "Signal": "BUY",
    "Entry Conviction": "IMMEDIATE",
    "Outcome": "HIT_TARGET",
    ...
  },
  {
    "Ticker": "MSFT",
    "Cutoff Date": "2025-01-05",
    "Signal": "AVOID",
    ...
  }
]
```

**Key Points:**
- Same ticker can appear multiple times (one per cutoff date)
- Each row is temporally independent
- Cutoff date ensures no forward-looking bias

---

## Running Multi-Date Backtests

### Weekly Backtest for Full Year 2025

```bash
cd /Users/sirajuddeeng/Siraj-Hustle/MyTradingSpace
source /Users/sirajuddeeng/Siraj-Hustle/.venv/bin/activate

python3 scripts/run_yearly_backtest.py \
  --year 2025 \
  --interval weekly \
  --workers 4 \
  --target-days 20 \
  --tickers-per-sector 9 \
  --fmp-api-key RZ8P7bENfukSirRglbdDQ30jIfjKsqSY
```

This generates **~52 cutoff dates** (weekly) for 2025:
- 2025-01-03 (Friday)
- 2025-01-10 (Friday)
- 2025-01-17 (Friday)
- ... (48 more)
- 2025-12-26 (Friday)

### Custom Date Range

```bash
python3 scripts/run_yearly_backtest.py \
  --start 2024-06-01 \
  --end 2025-05-31 \
  --interval biweekly \
  --workers 4 \
  --fmp-api-key YOUR_API_KEY
```

---

## Output Files

After running multi-date backtest:

```
data/output/backtests/yearly_2025/
├── all_results.json          ← Consolidated JSON with ALL cutoff dates
├── all_results.xlsx          ← Excel workbook with all results
└── run_summary.json          ← Statistics summary
```

### Summary Format

```json
{
  "total_records": 4628,
  "cutoff_dates": [
    "2025-01-03",
    "2025-01-10",
    ...
    "2025-12-26"
  ],
  "total_buy_signals": 782,
  "total_avoid_signals": 423,
  "total_hold_signals": 3214,
  "total_errors": 209,
  "outcomes": {
    "HIT_TARGET": 345,
    "HIT_STOP": 289,
    "EXPIRED": 148,
    "SKIP": 3637,
    "ERROR": 209
  }
}
```

---

## Data Integrity Checklist

✅ **No forward-looking bias:**
- Pattern detection uses data ≤ cutoff date only
- Entry price from cutoff date close
- Technical indicators calculated up to cutoff date

✅ **Outcome calculation uses future data:**
- Looks FORWARD from cutoff date to see if target/stop hit
- Simulates real trade over next 20 days

✅ **Temporal independence:**
- Each cutoff date analyzed independently
- No information leakage between periods

---

## Win Rate Calculation

From the JSON output:

```python
buy_trades = [r for r in data if r['Signal'] == 'BUY']
hit_target = len([r for r in buy_trades if r['Outcome'] == 'HIT_TARGET'])
hit_stop = len([r for r in buy_trades if r['Outcome'] == 'HIT_STOP'])

win_rate = hit_target / (hit_target + hit_stop) * 100
# Example: 345 / (345 + 289) = 54.4% win rate
```

---

## Example Analysis Query

```python
import json
import pandas as pd

# Load backtest results
with open('data/output/backtests/yearly_2025/all_results.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)

# Filter for high-confidence BUY signals
high_conf_buys = df[
    (df['Signal'] == 'BUY') & 
    (df['Confidence Score'] >= 70) &
    (df['Entry Conviction'] == 'IMMEDIATE')
]

# Calculate win rate
wins = high_conf_buys[high_conf_buys['Outcome'] == 'HIT_TARGET']
losses = high_conf_buys[high_conf_buys['Outcome'] == 'HIT_STOP']

print(f"High-confidence IMMEDIATE entries:")
print(f"  Total: {len(high_conf_buys)}")
print(f"  Wins: {len(wins)}")
print(f"  Losses: {len(losses)}")
print(f"  Win Rate: {len(wins)/(len(wins)+len(losses))*100:.1f}%")
```
