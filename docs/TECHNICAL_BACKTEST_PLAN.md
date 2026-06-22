# Technical-only backtest plan

**Status:** Active  
**Last updated:** 2026-06-20

## Goal

Rigorously backtest **Phoenix + 4 strategies** only. Primary metric: **TP** (bullish ∧ target hit) with **FN → 0**.

## Ground truth

- **Signal date:** e.g. `2025-07-01`
- **Eval window:** 15 calendar days (configurable)
- **Target hit:** Polygon daily **High** ≥ Phoenix `target_1` (or +5% fallback)

## Two different “signals” (important)

| Signal | Purpose |
|--------|---------|
| **Live `technical_signal_live`** | Enrichment gate — strict PASS rules before FA/agents run |
| **Backtest `technical_signal`** | Confusion-matrix evaluation — controlled by `--backtest-signal-profile` |

They are **intentionally different**. Live gate stays strict; backtest profile tunes recall vs precision.

---

## Live rules today (`enrichment_strict`)

From `agents/technical/fusion.py`:

1. **Hard filter fail** (below 200 DMA or &lt;50% above 52w low) → `bearish`
2. Phoenix **AVOID** → `bearish`
3. **Bullish only if** `pass_enrichment`:
   - Hard filters pass
   - Phoenix **BUY or WATCH**
   - Strategy consensus ≥2 entry triggers **OR** (Minervini trigger + Moglen regime)
   - Blend not bearish (unless Minervini+Moglen alt path)
4. **WATCH** without PASS → `neutral`
5. Else → `bearish`

**Why July 1 2025 IT had TP=0 under strict:**  
- **0 Phoenix BUY** in the 50-ticker sample  
- **26 stocks hit target:** 12 WATCH, 14 AVOID  
- Strict mapping → 0 bullish labels → **0 TP**, 14 FN, 12 missed TP  

---

## Backtest signal profiles

| Profile | Bullish when | Bearish when | Use case |
|---------|--------------|--------------|----------|
| `enrichment_strict` | Live PASS rules | Live bearish rules | Parity with production gate |
| `phoenix_buy_only` | Phoenix BUY | AVOID | Minimal Phoenix long bias |
| `phoenix_watch_bull` | BUY + WATCH | AVOID | More TP; FN on AVOID winners |
| **`phoenix_recall`** (default) | BUY + WATCH | **never** (AVOID→neutral) | **FN=0**, maximize TP from WATCH |

### July 1 2025 IT results (50 tickers, 15d eval)

| Profile | TP | FP | TN | FN | Missed TP* |
|---------|----|----|----|----|------------|
| enrichment_strict | 0 | 0 | 15 | 14 | 12 |
| **phoenix_recall** | **12** | **9** | **0** | **0** | **14** |

\*Target hit but signal not bullish (neutral under `phoenix_recall` = mostly Phoenix AVOID names).

---

## Commands

```bash
# Default: phoenix_recall
./bin/mts sector --sector "Information Technology" --date 2025-07-01

# Live-strict evaluation (old behavior)
python scripts/backtests/run_halal_sector_month_pilot.py \
  --sector "Information Technology" --signal-date 2025-07-01 \
  --single-master-json --backtest-signal-profile enrichment_strict
```

---

## Tuning loop (next)

1. **Raise TP above 12** — 14 winners were Phoenix **AVOID** on 2025-07-01; need Phoenix/scoring review or accept `phoenix_watch_bull` (adds FN)
2. **Lower FP (9)** — tighten from WATCH→bullish (e.g. require hard filter pass for WATCH bullish)
3. **Per-strategy matrix** — see which layer (Minervini/Moglen/…) aligns with target hit
4. **Re-test** June/July/ Aug 2025 across sectors before live buys

---

## Dashboard

**Research Lab → Backtest registry** — select IT / 2025-07-01 run; FN banner + technical heatmap.
