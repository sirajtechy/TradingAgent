---
name: risk-guardrails
description: Enforce risk-sensitive constraints for MyTradingSpace loop features. Block unsafe autonomous changes to scoring, fusion, or execution.
---

# Risk Guardrails Skill

Read `.loop/policies/risk-guardrails.md` before approving any loop-built change.

## Never auto-approve

- Live order placement, broker write paths
- Fusion weight changes (`OrchestratorSettings.full_context_weights`)
- Phoenix buy/watch thresholds without backtest
- Operator verdict logic that removes human decision mode
- Removal of abstain, hard filters, or extension guardrails

## Escalate when

- Backtest or fixture coverage missing for signal changes
- Lookahead in `as_of_date` handling
- Free fallback changes default production behavior silently

## Quant-risk focus for reviews

- Signal weighting and threshold edits
- Envelope mapping that changes trader-facing semantics
- Pipeline gating that hides agent output
