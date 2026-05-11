# Refactor Guardrails

These rules apply to mechanical refactors where the goal is zero behavior change.

## Zero Logic-Loss Rules

- Move code before changing code. A refactor may rename files, split modules, or reduce import fan-out, but it must not alter algorithmic outcomes.
- Keep public APIs stable unless a separate migration plan is approved. Existing imports, function signatures, return shapes, and CLI arguments must keep working.
- Preserve thresholds, sort order, tie-breakers, rounding, text fields used by callers, and error handling.
- Do not mix refactors with feature work, calibration changes, or performance rewrites.
- Use small module boundaries that match existing concepts. Avoid new abstractions unless they remove real duplication.
- Prefer git-aware moves when possible so review can distinguish moved code from edited code.
- Leave characterization tests optional for trivial moves, but add them when behavior is hard to inspect or widely used.

## Reviewer Checklist

- Public imports still resolve from their previous paths.
- Moved functions have identical inputs, outputs, defaults, and side effects.
- Thresholds still come from the same settings/config objects.
- Candidate ordering, priority rules, and tie-breakers are unchanged.
- No data-source behavior changed: no new network calls, caches, or fallback providers.
- Tests cover at least one representative path through the moved code.
- The diff separates documentation, tests, and refactor edits clearly enough to review.

## Verification Ladder

1. Import smoke: validate the old public import path.
2. Focused unit tests: synthetic fixtures for moved behavior.
3. Full local test suite: `pytest tests/`.
4. Optional characterization: compare before/after JSON outputs for fixed tickers and dates.
5. Optional backtest smoke: run the smallest relevant script against a pinned ticker/universe/date.

Escalate up the ladder when a refactor touches shared contracts, scoring, orchestration, or backtest output.
