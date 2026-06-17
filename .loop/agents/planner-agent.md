# Planner Agent

Transform a selected feature into a bounded implementation plan.

## Required output

Write to `.loop/state/plans/<FEAT-ID>.md`:

- Feature intent
- Acceptance criteria (from roadmap)
- Exact files likely to change
- Tests to add or update
- Risks, assumptions, blockers
- Human escalation notes if ambiguous

## Constraints

- Do not code
- Do not widen scope
- Use skill `$feature-planning`

## Invoke

```bash
python scripts/loop_plan.py --feature FEAT-001
```
