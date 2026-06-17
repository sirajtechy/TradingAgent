# Feature selection policy

Only auto-select work items that satisfy **all** of:

- Clearly scoped (one feature card, bounded file blast radius)
- Deterministic acceptance criteria listed in `roadmap.yaml`
- Testable with existing or easily added fixtures
- `auto_eligible: true` in roadmap
- `risk_level` is `low` or `medium` (medium requires reviewer + quant-risk pass)
- Does not touch broker execution or live order paths

Defer to human triage when **any** of:

- Requirements ambiguous
- Spans many subsystems without a plan
- Changes execution semantics or fusion weights without review
- Requires undocumented business judgment
- Reviewer or quant-risk agent escalates

Selection score weights (used by `loop_select.py`):

| Factor | Weight |
|--------|--------|
| Roadmap priority (high=3, medium=2, low=1) | 40% |
| Risk level (low=3, medium=2, high=0) | 30% |
| Has acceptance criteria count ≥ 3 | 20% |
| Epic EPIC-002 infra boost | 10% |
