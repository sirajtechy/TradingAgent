# Orchestrator — CWAF Fusion Rules

> Actual rules from `agents/orchestrator/fusion.py` and `agents/orchestrator/config.py`.

---

## Architecture

- CWAF = Confidence-Weighted Asymmetric Fusion
- Takes `experimental_score` from both Technical Agent and Fundamental Agent
- 4-layer decision tree: Error → Agreement → Single-Agent → Conflict
- Anti-bullish guardrails applied after every bullish decision
- Output: final_signal, final_confidence, orchestrator_score
- **The orchestrator is the MANDATORY gateway for all trade predictions.** No prediction ever bypasses it. `predict_trade()` always calls `orchestrator.service.analyze_ticker()` first, which runs both TA and FA internally in parallel, then fuses via CWAF.

---

## Confidence Formula

Each agent's confidence = distance from nearest band boundary, normalised 0–1.

```
confidence = min(abs(score - nearest_boundary) / 25.0, 1.0)
```

**Tech band boundaries:** `[35.0, 50.0, 60.0, 75.0]`
**Fund band boundaries:** `[40.0, 62.0, 70.0, 85.0]`

Deep inside a band → high confidence. Near boundary → low confidence.

---

## Band → Signal Mapping

**Orchestrator thresholds (tighter than individual agents):**

| Score | Signal |
|---|---|
| ≥ 62.0 | bullish |
| 38.0–61.9 | neutral |
| < 38.0 | bearish |

---

## Fusion Weights

| Scenario | Tech Weight | Fund Weight |
|---|---|---|
| Agreement (both bullish or bearish) | 0.45 | 0.55 |
| Agreement (both neutral) | 0.50 | 0.50 |
| Tech only directional (fund neutral) | 0.85 | 0.15 |
| Fund only directional (tech neutral) | 0.15 | 0.85 |
| Conflict (winner dominates) | 0.30 loser, 0.70 winner |
| Conflict (equal confidence) | 0.50 | 0.50 |

---

## Layer 0 — Error Handling

| Condition | Result |
|---|---|
| Both agents error | neutral, confidence = 0, score = 50 |
| Tech errors only | Use fund output alone (weight: fund = 1.0) |
| Fund errors only | Use tech output alone (weight: tech = 1.0) |

---

## Layer 1 — Agreement (both same signal)

### Both Bullish
- `score = 0.45 × tech_score + 0.55 × fund_score`
- `confidence = max(tech_conf, fund_conf) × 1.15` (bullish agreement bonus, capped at 1.0)
- Apply anti-bullish guardrails before returning

### Both Bearish
- `score = 0.45 × tech_score + 0.55 × fund_score`
- `confidence = max(tech_conf, fund_conf) × 1.20` (bearish agreement bonus, capped at 1.0)
- Signal from score-to-signal mapping (no guardrails needed)

### Both Neutral
- `score = 0.50 × tech_score + 0.50 × fund_score`
- `confidence = 0.70` (fixed)
- Signal = neutral

---

## Layer 2 — Single-Agent Directional (one neutral, one directional)

### Tech Bullish + Fund Neutral
- Weights: tech 0.85, fund 0.15
- `confidence = tech_confidence × 0.85` (tech_only_discount)
- If fund data_quality = "poor": `confidence × 0.90` (additional discount)
- Apply anti-bullish guardrails

### Tech Bearish + Fund Neutral
- Weights: tech 0.85, fund 0.15
- `confidence = tech_confidence × 0.85`
- Signal from score-to-signal mapping

### Fund Bullish + Tech Neutral
- Weights: tech 0.15, fund 0.85
- `confidence = fund_confidence × 0.90` (fund_only_discount)
- Apply anti-bullish guardrails

### Fund Bearish + Tech Neutral
- Weights: tech 0.15, fund 0.85
- `confidence = fund_confidence × 0.90`
- Signal from score-to-signal mapping

---

## Layer 3 — Conflict (opposite directions)

Resolve by comparing confidence gap (threshold = 0.15):

### Fund Dominates (`fund_conf > tech_conf + 0.15`)
- Winner weight: 0.70 fund, 0.30 tech
- `confidence = fund_conf × 0.75` (conflict_winner_discount_fa)
- Signal = fund's signal
- Apply guardrails

### Tech Dominates (`tech_conf > fund_conf + 0.15`)
- Winner weight: 0.70 tech, 0.30 fund
- `confidence = tech_conf × 0.70` (conflict_winner_discount_ta)
- Signal = tech's signal
- Apply guardrails

### Near-Equal (gap < 0.15 both ways)
- Equal weights: 0.50 / 0.50
- `confidence = 0.30` (conflict_abstain_confidence)
- Signal = neutral (abstain)
- Apply guardrails

---

## Anti-Bullish Guardrails

Applied after every path that proposes a bullish signal.

### Guardrail 1 — Bullish Confirmation Requirement
If ALL of these are true:
- `require_bullish_confirmation = True` (default)
- Proposed signal = bullish
- Tech band = "mixed_positive" (weakest bullish, score 50–59)
- Fund signal = bearish

→ **Downgrade to neutral.** Weak tech bullish + bearish fundamentals is not trustworthy.

### Guardrail 2 — Score-Based Override
After all other logic, the final signal is re-derived from the orchestrator score:
- `score ≥ 62` → bullish
- `38 ≤ score < 62` → neutral
- `score < 38` → bearish

This overrides the proposed signal if the weighted score disagrees. The score is the ground truth.

---

## Data Quality Handling

Fund agent data quality derived from coverage_ratio:
- coverage ≥ 0.80 → "good"
- coverage ≥ 0.50 → "fair"
- coverage < 0.50 → "poor"

When data quality = "poor":
- Additional discount of 0.90 applied to confidence in single-agent scenarios

---

## Configuration Constants Summary

| Parameter | Value |
|---|---|
| bullish_threshold | 62.0 |
| bearish_threshold | 38.0 |
| confidence_max_distance | 25.0 |
| bullish_agreement_bonus | 1.15 |
| bearish_agreement_bonus | 1.20 |
| tech_only_discount | 0.85 |
| fund_only_discount | 0.90 |
| poor_data_quality_discount | 0.90 |
| conflict_confidence_gap | 0.15 |
| conflict_winner_discount_fa | 0.75 |
| conflict_winner_discount_ta | 0.70 |
| conflict_abstain_confidence | 0.30 |
| agreement_neutral_confidence | 0.70 |
| require_bullish_confirmation | True |

---

*Updated: 2026-04-05 — Extracted from agents/orchestrator/fusion.py & config.py. Added prediction gateway rule.*