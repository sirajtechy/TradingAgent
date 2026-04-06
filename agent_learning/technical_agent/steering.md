# Technical Agent — Scoring Rules

> Actual scoring rules from `agents/technical/rules.py`.

---

## Architecture

- 12 independent frameworks, each scores 0–100 (neutral base = 50)
- Weighted composite = Σ(framework_score × weight) / Σ(weights of applicable frameworks)
- Signal-alignment confidence = % of frameworks agreeing on direction (v3)
- All helpers are pure functions; `evaluate_snapshot()` is the single entry point

---

## Framework Weights (12 total, sum = 1.00)

| # | Framework | Weight | Purpose |
|---|---|---|---|
| 1 | EMA Trend Alignment | 0.14 | Trend backbone + ROC overlay |
| 2 | MACD System | 0.11 | Trend + momentum combo |
| 3 | RSI Regime | 0.11 | Gold-standard oscillator |
| 4 | Bollinger Bands | 0.08 | Volatility context |
| 5 | Volume (OBV + CMF) | 0.08 | Leading indicator + distribution detection |
| 6 | ADX + Stochastic | 0.06 | Trend strength + mean-reversion |
| 7 | Pattern Recognition | 0.07 | Chart breakout confirmation |
| 8 | Ichimoku Cloud | 0.10 | Comprehensive trend / support-resistance |
| 9 | Momentum Composite | 0.07 | ROC + Williams %R + CCI |
| 10 | Supertrend | 0.06 | Trend direction with ATR bands |
| 11 | Volatility Squeeze | 0.06 | Bollinger inside Keltner detection |
| 12 | Entry/Exit Rules | 0.06 | Multi-indicator entry confirmation |

---

## Framework Scoring Rules (all base = 50)

### 1. EMA Trend Alignment

| Condition | Points |
|---|---|
| Price > EMA-200 | +15 |
| Price < EMA-200 | −15 |
| Price > EMA-50 | +12 |
| Price < EMA-50 | −12 |
| Price > EMA-20 | +7 |
| Price < EMA-20 | −7 |
| EMA stack: 20 > 50 > 200 | +7 |
| EMA stack: 20 < 50 < 200 | −7 |
| Golden Cross (SMA50 > SMA200) | +7 |
| Death Cross (SMA50 < SMA200) | −7 |
| ROC-12 > +5 | +6 |
| ROC-12 > 0 | +3 |
| ROC-12 < 0 | −4 |
| ROC-12 < −2 | −8 |

ROC overlay catches momentum fade while EMAs remain bullishly stacked (lagging indicator fix).

### 2. MACD System

| Condition | Points |
|---|---|
| MACD > signal line | +15 |
| MACD < signal line | −15 |
| MACD > 0 (above centerline) | +10 |
| MACD < 0 | −10 |
| Histogram rising | +7 |
| Histogram falling | −7 |
| Bullish divergence | +13 |
| Bearish divergence | −13 |

### 3. RSI Regime

| Condition | Points |
|---|---|
| RSI 50–60 | +10 |
| RSI 60–70 (strong bull) | +15 |
| RSI 40–50 | −8 |
| RSI 30–40 | −15 |
| RSI < 30 (oversold reversal) | +5 |
| RSI > 70 (overbought) | −5 |
| RSI falling from 65–80 zone | −8 (overbought-exit detection) |

### 4. Bollinger Bands

| Condition | Points |
|---|---|
| %B > 0.8 (above upper) | −10 |
| %B < 0.2 (below lower) | +10 |
| %B 0.5–0.8 | +5 |
| %B 0.2–0.5 | −5 |
| %B extreme + bandwidth combo | −8 (overbought reversal) |

### 5. Volume (OBV + CMF)

| Condition | Points |
|---|---|
| OBV slope positive (10-bar) | +12 |
| OBV slope negative | −12 |
| CMF > +0.10 (accumulation) | +8 |
| CMF < −0.10 (distribution) | −8 |
| CMF −0.10 to +0.10 | 0 |

CMF detects distribution (smart money selling) even when price is rising.

### 6. ADX + Stochastic

| Condition | Points |
|---|---|
| ADX > 25 + DI+ > DI− | +15 (strong uptrend) |
| ADX > 25 + DI− > DI+ | −15 (strong downtrend) |
| ADX < 20 | 0 (no trend) |
| Stoch %K > %D + both < 80 | +8 (bullish cross) |
| Stoch %K < %D + both > 20 | −8 (bearish cross) |

### 7. Pattern Recognition

| Condition | Points |
|---|---|
| Bullish pattern confirmed | +confidence × 15 |
| Bearish pattern confirmed | −confidence × 15 |
| Max contribution cap | ±18 |

Recency decay applied — older patterns score less. Conflicting patterns net-cancel.

### 8. Ichimoku Cloud

| Condition | Points |
|---|---|
| Price > Kumo (above cloud) | +15 |
| Price < Kumo (below cloud) | −15 |
| Tenkan > Kijun (TK cross bull) | +10 |
| Tenkan < Kijun | −10 |
| Future Kumo bullish | +5 |
| Future Kumo bearish | −5 |

### 9. Momentum Composite

| Condition | Points |
|---|---|
| ROC-12 > +3 | +8 |
| ROC-12 < −3 | −8 |
| Williams %R > −20 (overbought) | −5 |
| Williams %R < −80 (oversold) | +5 |
| CCI > +100 | +7 |
| CCI < −100 | −7 |

---

## Composite → Band → Signal

| Score | Band | Signal |
|---|---|---|
| ≥ 75 | strong | bullish |
| 60–74 | good | bullish |
| 50–59 | mixed_positive | bullish (weakest) |
| 35–49 | mixed | neutral |
| < 35 | weak | bearish |

---

## Confidence: Signal Alignment (v3)

Confidence = % of 12 frameworks agreeing on same direction.

| Alignment | Label | Score |
|---|---|---|
| ≥ 75% agree | high | 80+ |
| 50–74% agree | medium | 55 |
| < 50% agree | low | 25 |

Fallback: ADX ≥ 40 = high, ≥ 20 = medium, < 20 = low.

---

## Risk Management Output (v3)

Every bullish signal outputs:
- `stop_loss` = entry − 2 × ATR(14)
- `target_price` = entry + 3 × ATR(14) → 1.5:1 reward/risk
- `trade_duration_days` = from per-ticker learned duration model
- `transaction_cost_pct` = 0.10%
- `slippage_pct` = 0.05%
- `net_expected_profit_pct` = expected − friction

---

## Output Key

Score stored under `experimental_score` key (NOT `composite_score`). The orchestrator reads this field.

---

*Updated: 2026-04-04 — Extracted from agents/technical/rules.py*