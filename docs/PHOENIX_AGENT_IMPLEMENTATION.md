# Phoenix Agent — Implementation Document

> Contract note: `PHOENIX_AGENT_SPEC.md` is the normative source for Phoenix public APIs, output keys, thresholds, and pattern priority. This implementation document is retained as build history and rationale.

**Based on:** @pheonix_trader (Himanshu Sharma) strategy  
**Source file:** `trading-strategies/phoneix-trader.md`  
**Status:** Ready to implement — new session kickoff doc  
**Target path:** `agents/phoenix/`

---

## Context

This document captures the full implementation plan for a new standalone trading agent
that mirrors the @pheonix_trader strategy. It was designed in the session where the
existing Technical Agent gap analysis was done against the Phoenix Trader playbook.

**Key decision:** Build as a completely separate agent (`agents/phoenix/`), NOT a
modification of the existing `agents/technical/`. The two agents can eventually be
fused via the orchestrator as a 4th signal source.

**Existing infrastructure to reuse:**
- `agents/polygon_data/` — Polygon OHLCV client (already works, has SMA/bar support)
- `agents/oneil/stage_analysis.py` — Weinstein stage classifier (adapt to daily bars)
- `agents/technical/patterns.py` — Flat Base Breakout + Pocket Pivot (already added in current session)
- LangGraph pattern from `agents/technical/graph.py` and `agents/orchestrator/graph.py`

---

## Phoenix Trader Strategy Summary (the spec)

### Core Philosophy
- **Price structure over indicators** — setups not signals
- **Volume is the only leading signal** — breakout on 2× avg volume or skip
- **Rejected indicators:** RSI, MACD, Stochastics, Bollinger Bands (all lag)
- **Only trade Stage 2** — cash in Stage 1, 3, 4

### Stock Selection Hard Filters
1. Price must be **above 200-day MA** (hard prerequisite)
2. Price must be **≥50% above its 52-week low** (in position of strength)
3. Belongs to top 1-2 sectors/themes (not automated — manual context)
4. Earnings catalyst / business catalyst present (not automated — future enhancement)

### Indicators Used
| Indicator | Role |
|-----------|------|
| MA10 (SMA) | Momentum + trailing stop |
| MA20 (SMA) | Support + trailing stop |
| MA200 (SMA) | Trend filter (hard prerequisite) |
| 40-week MA | Macro trend context |
| Volume | Primary confirmation — 2× avg required |

### 4 Stage Analysis
| Stage | Conditions | Action |
|-------|-----------|--------|
| 1 — Accumulation | Below/near MA20, MA20 flat/declining | WATCH |
| **2 — Momentum** | Price > MA20 > MA50 > MA200, MAs rising | **TRADE** |
| 3 — Exhaustion | Price extended, MA20 flattening, wide/loose | REDUCE |
| 4 — Decline | Price < MA200, MA200 declining | AVOID |

### 3 Core Patterns
1. **VCP (Volatility Contraction Pattern)** — Primary pattern
2. **Flat Base** — 4-8 weeks sideways, <15% range, volume contracting
3. **Tight Flag / Pocket Pivot** — Sharp pole + tight flag + volume dryup

### 4 Entry Methods
1. **Standard Breakout** — volume > 2× avg → BUY
2. **Pivot Breakout** — breakout from pivot inside a larger base
3. **Shakeout** — false breakdown → snap back above support
4. **Pullback** — retrace to MA10 or MA20 after breakout

### Risk Management
| Rule | Detail |
|------|--------|
| Stop Loss | LOC — Low Of breakout Candle (hard stop) |
| Trailing Stop | Hold above MA10 → trail to MA20 → exit on MA20 break + volume |
| Position Size | Max 1-2% capital risk per trade |
| Volume Filter | Low-volume breakout = SKIP entirely |

---

## File Structure to Build

```
agents/phoenix/
├── __init__.py           — exports: analyze_ticker, PhoenixSignal
├── service.py            — public API: analyze_ticker(ticker, as_of_date)
├── graph.py              — LangGraph 8-node pipeline
├── models.py             — all dataclasses / TypedDicts
├── config.py             — PhoenixSettings (all tunable thresholds)
├── data_client.py        — Polygon wrapper → SMAs, volume series
├── filters.py            — 200DMA + 52w-low hard pre-filters
├── stage_classifier.py   — Stage 1/2/3/4 daily classifier
├── patterns.py           — VCP, Flat Base, Tight Flag, Shakeout, Pullback
├── entry.py              — 4 entry type mappers + entry price computation
├── risk.py               — LOC stop, trailing stops, position sizing, R/R
├── scoring.py            — Phoenix composite score (no RSI/MACD/Bollinger)
├── reporting.py          — human-readable text report builder
├── backtest.py           — monthly backtest engine
└── exceptions.py         — PhoenixAgentError, HardFilterRejected, StageFilterRejected
```

---

## LangGraph Pipeline (8 nodes)

```
START
  → fetch_data          (Polygon: 500 daily bars ending at as_of_date)
  → apply_hard_filters  (200DMA + 52w-low; fail-fast → AVOID if rejected)
  → classify_stage      (Stage 1/2/3/4 from daily SMAs)
  → detect_patterns     (VCP / Flat Base / Tight Flag / Shakeout / Pullback)
  → evaluate_entry      (which of 4 entry types is active + entry price)
  → compute_risk        (LOC stop / target / R/R / position size)
  → build_score         (0-100 Phoenix composite)
  → render_report       (human-readable text report)
END

Fail-fast exits:
  apply_hard_filters → AVOID (if below 200DMA or <50% above 52w low)
  classify_stage → WATCH/AVOID (if Stage 1, 3, or 4)
```

---

## models.py — Data Contracts

```python
@dataclass
class PhoenixRequest:
    ticker: str
    as_of_date: date

@dataclass
class SMABundle:
    sma10: Optional[float]
    sma20: Optional[float]
    sma50: Optional[float]
    sma200: Optional[float]
    sma40w: Optional[float]   # 200-bar rolling (40 weeks)

@dataclass
class PhoenixSnapshot:
    request: PhoenixRequest
    bars: List[OHLCVBar]      # 500 daily bars, oldest-first
    smas: SMABundle           # latest values
    vol_avg_20: float         # 20-bar average volume
    high_52w: float
    low_52w: float
    as_of_price: float
    as_of_price_date: date

@dataclass
class StageResult:
    stage: int                # 1, 2, 3, or 4
    label: str                # "Accumulation" / "Momentum" / "Exhaustion" / "Decline"
    action: str               # "WATCH" / "TRADE" / "REDUCE" / "AVOID"
    ma_alignment: bool        # price > ma20 > ma50 > ma200
    ma_slopes: Dict[str, str] # rising/flat/falling per SMA
    notes: List[str]

@dataclass
class PatternMatch:
    pattern_name: str         # "VCP" / "Flat Base" / "Tight Flag" / "Shakeout" / "Pullback"
    confirmed: bool           # breakout confirmed (price + volume)
    volume_confirmed: bool    # volume >= 2× avg
    pivot_price: float        # the breakout level
    confidence: float         # 0.0 – 1.0
    vcp_contractions: int     # for VCP: number of contractions detected (1–3)
    base_depth_pct: float     # % depth of the base/pattern
    description: str

@dataclass
class EntrySetup:
    entry_type: str           # "standard_breakout" / "pivot" / "shakeout" / "pullback"
    entry_price: float        # recommended entry price
    trigger_description: str

@dataclass
class RiskLevels:
    stop_price: float         # LOC — low of breakout candle
    stop_pct: float           # % risk from entry to stop
    target_1: float           # 1× measured move
    target_2: float           # 1.5× measured move
    reward_risk: float        # R/R ratio
    position_size_shares: Optional[float]  # based on 1% capital risk
    trail_stop_ma: str        # "MA10" or "MA20" (current trailing stop level)

@dataclass
class PhoenixSignal:
    ticker: str
    as_of_date: date
    signal: str               # "BUY" / "WATCH" / "AVOID"
    stage: StageResult
    pattern: Optional[PatternMatch]
    entry: Optional[EntrySetup]
    risk: Optional[RiskLevels]
    score: float              # 0–100
    score_breakdown: Dict[str, float]  # volume/structure/pattern/stage components
    hard_filter_passed: bool
    hard_filter_reason: Optional[str]
    report: str
    warnings: List[str]
```

---

## config.py — PhoenixSettings

```python
@dataclasses.dataclass(frozen=True)
class PhoenixSettings:
    # Volume
    volume_breakout_multiple: float = 2.0      # Phoenix requires 2× (strict)
    volume_dryup_threshold: float = 0.75       # base volume < 75% avg = drying up
    volume_lookback_bars: int = 20             # bars for avg volume

    # MA periods (SMA, not EMA)
    ma_short: int = 10
    ma_mid: int = 20
    ma_long: int = 50
    ma_trend: int = 200
    ma_40w: int = 200                          # 40 weeks ≈ 200 trading days

    # Hard filters
    above_200dma_required: bool = True
    above_52w_low_pct: float = 0.50            # must be 50%+ above 52w low

    # Stage 2 gate
    stage2_only: bool = True                   # skip Stage 1, 3, 4

    # Pattern thresholds
    flat_base_max_range_pct: float = 0.15      # <15% range (Phoenix: 10-15%)
    flat_base_min_bars: int = 20               # ~4 weeks minimum
    flat_base_max_bars: int = 120              # ~6 months maximum
    vcp_max_contractions: int = 3
    vcp_min_depth_pct: float = 0.10            # each contraction min 10%
    vcp_contraction_ratio: float = 0.50        # each contraction < 50% of prior
    flag_pole_min_gain_pct: float = 8.0
    flag_pole_max_bars: int = 15
    flag_max_retrace_pct: float = 0.50
    shakeout_max_bars_below: int = 3           # max bars below support before snap-back

    # Scoring weights
    weight_volume: float = 0.40
    weight_structure: float = 0.30
    weight_pattern: float = 0.20
    weight_stage: float = 0.10

    # Signal thresholds
    buy_threshold: float = 70.0
    watch_threshold: float = 50.0

    # Risk
    stop_buffer_pct: float = 0.001            # 0.1% below LOC
    target_multiplier_1: float = 1.0           # 1× measured move
    target_multiplier_2: float = 1.5           # 1.5× measured move
    capital_risk_pct: float = 0.01             # 1% capital at risk
```

---

## stage_classifier.py — Stage Logic

```python
def classify_stage(snapshot: PhoenixSnapshot, settings: PhoenixSettings) -> StageResult:
    """
    Daily-bar Stage 1/2/3/4 classification using SMA10, SMA20, SMA50, SMA200.

    Stage 2 criteria (ALL must be true):
      1. price > SMA20 > SMA50 > SMA200
      2. SMA20 slope = rising (current > prior by > 0.3%)
      3. SMA200 slope = rising or flat (not falling)
      4. Volume expanding (recent 10-bar avg > prior 10-bar avg)

    Stage 4 criteria (ANY sufficient):
      1. price < SMA200
      2. SMA200 slope = falling

    Stage 3 criteria (between 2 and 4):
      1. price > SMA200 but SMA20 flattening or declining
      2. Wide & loose action (ATR expanding vs base ATR)

    Stage 1: everything else
    """
```

---

## patterns.py — 5 Pattern Detectors

### VCP Algorithm (most complex)
```
1. Find the most recent swing high in last 60-120 bars (base peak)
2. Measure pullback 1 from peak:
   - Find the deepest trough after the peak
   - depth_1 = (peak - trough_1) / peak
   - range_1 = (max_high - min_low) in that contraction window
3. Measure recovery 1, then pullback 2:
   - depth_2 must be < depth_1 * 0.50 (≤50% of prior contraction)
   - range_2 < range_1 * 0.50
   - volume in contraction_2 < volume in contraction_1 (drying up)
4. Measure recovery 2, then pullback 3:
   - depth_3 < depth_2 * 0.50
   - range_3 < range_2 * 0.50 (very tight — "V" contracting to a point)
   - volume near zero
5. Pivot = highest close during pullback_3
6. FIRE if: last_close > pivot AND volume[-1] >= vol_avg_20 * 2.0
7. Confidence: based on contraction symmetry + volume decline quality + recency
```

### Flat Base Algorithm
```
Same as existing _detect_flat_base_breakout in agents/technical/patterns.py
BUT tighter: max range 15% (not 25%), volume must be CONTRACTING during base
(vol_avg last 10 bars of base < vol_avg first 10 bars of base)
Volume on breakout: must be >= 2.0× avg (not 1.5×)
```

### Tight Flag Algorithm
```
Same as existing Bull Flag detector
BUT:
  - Max retrace of flagpole: 50%
  - Volume on breakout: >= 2.0× avg
  - Add volume dryup check during flag body
```

### Shakeout Algorithm
```
1. Identify a key support level:
   - Option A: MA20 value
   - Option B: Prior base low (lowest low of last 20-bar base)
2. Find bars where close dipped BELOW support (lookback 10 bars)
3. That dip must last <= 3 bars (shakeout, not breakdown)
4. Volume during dip < 20-bar avg (no institutional selling = support intact)
5. Most recent close must be ABOVE support level (snap-back confirmed)
6. Confidence: higher if volume was low during dip, snap-back was fast
```

### Pullback to MA10/MA20 Algorithm
```
1. Check if there was a confirmed breakout in the prior 20 bars
   (any bullish pattern that fired, or: price made a 52w high within 20 bars)
2. Current price is within 2% of MA10 OR MA20
3. Volume during pullback < 0.75× avg (drying up = healthy pullback)
4. Last bar closed UP (bounce starting)
5. Signal: BUY on next open above the MA
```

---

## scoring.py — Phoenix Composite Score

```
Total score = 0-100. NO RSI, MACD, Bollinger, Stochastics.

VOLUME COMPONENT (40 pts max):
  - vol_trend_score (0-15):  recent 10-bar avg > prior 10-bar avg? Rising trend.
  - breakout_vol_score (0-15): last bar vol / avg. 2× = full 15pts. Scales linearly.
  - base_dryup_score (0-10): volume contracting in base = accumulation signal.

PRICE STRUCTURE / MA COMPONENT (30 pts max):
  - above_200dma (0 or 10):   HARD — 10pts if above, 0 if below
  - ma_alignment (0 or 8):    price > ma20 > ma50 > ma200 = 8pts
  - ma_slopes (0-7):          +2 per rising SMA (ma20, ma50, ma200)
  - proximity_to_ma (0-5):    price within 5-10% of MA20 = setup area

PATTERN QUALITY COMPONENT (20 pts max):
  - pattern_confirmed (0 or 12):  breakout confirmed (price + volume) = 12pts
  - pattern_confidence (0-5):     pattern.confidence * 5
  - recency (0-3):                pattern fired in last 5 bars = 3pts

STAGE COMPONENT (10 pts max):
  - Stage 2 = 10pts
  - Stage 1 = 3pts (forming)
  - Stage 3 = 2pts (risky)
  - Stage 4 = 0pts (but should never reach here due to hard filter)

Signal mapping:
  score >= 70 → BUY
  score >= 50 → WATCH
  score < 50  → AVOID
```

---

## entry.py — Entry Type Mapping

```python
def evaluate_entry(
    pattern: PatternMatch,
    snapshot: PhoenixSnapshot,
    settings: PhoenixSettings,
) -> EntrySetup:
    """
    Map detected pattern to one of Phoenix's 4 entry types.

    Priority order:
      1. If VCP or Flat Base or Tight Flag + volume confirmed → Standard Breakout
      2. If VCP with pivot inside larger base → Pivot Breakout
      3. If Shakeout pattern → Shakeout Entry
      4. If Pullback to MA10/MA20 → Pullback Entry
    """
```

---

## risk.py — Risk & Position Sizing

```python
def compute_risk(
    entry: EntrySetup,
    pattern: PatternMatch,
    snapshot: PhoenixSnapshot,
    settings: PhoenixSettings,
    account_size: float = 100_000,
) -> RiskLevels:
    """
    LOC stop: low of the breakout candle (bars[-1].low)
    Stop price: LOC * (1 - settings.stop_buffer_pct)
    Risk per share: entry_price - stop_price
    Target 1: entry_price + base_height * settings.target_multiplier_1
    Target 2: entry_price + base_height * settings.target_multiplier_2
    R/R: (target_1 - entry_price) / (entry_price - stop_price)
    Position size: (account_size * settings.capital_risk_pct) / risk_per_share
    Trail: if entry > ma10 and price > ma10 → trail on MA10
           if ma10 broken → shift trail to MA20
    """
```

---

## service.py — Public API

```python
def analyze_ticker(
    ticker: str,
    as_of_date: Optional[str] = None,
    settings: Optional[PhoenixSettings] = None,
    account_size: float = 100_000,
) -> Dict[str, Any]:
    """
    Full Phoenix Trader analysis for a single ticker at a cutoff date.

    Returns dict with keys:
        ticker, as_of_date, signal, stage, pattern, entry,
        risk, score, score_breakdown, hard_filter_passed,
        hard_filter_reason, report, warnings
    """
```

---

## Integration Plan

### Run Phoenix standalone
```bash
python scripts/run_orchestrator_tickers.py --tickers CRWD --date 2026-04-30 --strategy phoenix
python scripts/run_orchestrator_tickers.py --tickers CRWD,AMD,NVDA --date 2026-04-30 --strategy phoenix
python scripts/run_orchestrator_tickers.py --sector Technology --date 2026-04-30 --strategy phoenix
```

### Run both strategies side-by-side
```bash
python scripts/run_orchestrator_tickers.py --tickers CRWD --date 2026-04-30 --strategy both
```

### Backtest Phoenix agent
```bash
python backtests/run_phoenix.py --sector Technology --workers 6
python backtests/run_phoenix.py --sector Technology --date-from 2025-01-01 --date-to 2026-04-30
```

---

## Build Order (4 Sessions)

### Session 1 — Foundation
Files: `exceptions.py`, `config.py`, `models.py`, `data_client.py`, `filters.py`
Checkpoint: Can instantiate PhoenixSnapshot, run hard filters, see AVOID/PASS result

### Session 2 — Stage + Patterns
Files: `stage_classifier.py`, `patterns.py`
Checkpoint: Can classify Stage 1/2/3/4 for any ticker + detect VCP/Flat Base/Flag/Shakeout/Pullback

### Session 3 — Entry + Risk + Scoring
Files: `entry.py`, `risk.py`, `scoring.py`
Checkpoint: Given a detected pattern, get entry price, stop, target, R/R, and composite score

### Session 4 — Graph + Service + Reporting + Backtest
Files: `graph.py`, `service.py`, `reporting.py`, `backtest.py`, `__init__.py`
+ Update `scripts/run_orchestrator_tickers.py` for `--strategy` flag
Checkpoint: Full end-to-end run like current agent

---

## Gap Analysis vs Existing Technical Agent

| Gap | Current Technical Agent | Phoenix Agent |
|-----|------------------------|---------------|
| VCP Pattern | Not implemented | Implemented (primary pattern) |
| Stage 2 gate | No stage classifier | Hard gate — Stage 4 → AVOID |
| 200 DMA hard filter | Soft (EMA in score) | Hard prerequisite — fails fast |
| 52-week low filter | Not implemented | 50% above 52w low required |
| Volume threshold | 1.5× for breakout | 2.0× (Phoenix requirement) |
| RSI weight | 11% | 0% (explicitly rejected) |
| MACD weight | 11% | 0% (explicitly rejected) |
| Bollinger weight | 6% | 0% (explicitly rejected) |
| Shakeout detection | Not implemented | Pattern 4 |
| Pullback entry | Not implemented | Pattern 5 |
| LOC stop | Not computed | Core output |
| Trailing stop logic | Not computed | MA10 → MA20 trail |
| Position sizing | Not computed | 1% capital risk per trade |

---

## Changes Already Made in Current Session

The following changes were made to the existing Technical Agent (NOT Phoenix — these are
pre-work improvements that benefit both agents):

1. **`agents/technical/patterns.py`** — Added `_detect_flat_base_breakout()` and
   `_detect_pocket_pivot()` detectors, registered in `detect_all_patterns()`

2. **`agents/technical/rules.py`** — Increased `pattern_recognition` weight from
   0.07 → 0.12 (redistributed from bollinger 0.08→0.06, adx_stochastic 0.06→0.05,
   volatility_squeeze 0.06→0.05, entry_exit_rules 0.06→0.05)

3. **`agents/orchestrator/config.py`** — Changed `fund_data_source` from
   `"yfinance"` → `"fmp"` then back to `"yfinance"` (yfinance is the working free
   source; FMP returns 402 on free tier for income statements)

4. **`agents/fundamental/service.py`** — Made yfinance import lazy (only loads when
   `data_source="yfinance"` is requested, avoiding module-level import crash)

5. **`scripts/run_orchestrator_tickers.py`** — New script: run 1 ticker, N tickers,
   or a full sector at a required cutoff date. Supports `--tickers` or `--sector`.

---

## Validation Tests to Run After Each Session

```bash
# After Session 1
python -c "
from agents.phoenix.data_client import PhoenixDataClient
from agents.phoenix.filters import apply_hard_filters
import os; os.chdir('MyTradingSpace')
client = PhoenixDataClient()
snap = client.build_snapshot('CRWD', '2026-04-10')
result = apply_hard_filters(snap)
print(result)
"

# After Session 2
python -c "
from agents.phoenix.stage_classifier import classify_stage
# ... print stage for CRWD at 2026-03-30 (should be Stage 1 or borderline)
# ... print stage for CRWD at 2026-04-30 (should be Stage 2)
"

# After Session 4 (full run)
python scripts/run_orchestrator_tickers.py --tickers CRWD --date 2026-04-30 --strategy phoenix
# Expected: BUY, Stage 2, VCP or Flat Base confirmed, LOC stop shown
```

---

*Document generated: May 6, 2026 | Session: MyTradingSpace multi-agent architecture*
