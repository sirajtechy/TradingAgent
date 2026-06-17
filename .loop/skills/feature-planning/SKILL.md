---
name: feature-planning
description: Turn a selected MyTradingSpace feature into a bounded implementation plan with file scope, acceptance criteria, tests, and rollback notes. Use before any loop implementer runs.
---

# Feature Planning Skill

## Goals

- Produce a bounded implementation plan in `.loop/state/plans/<FEAT-ID>.md`
- Keep blast radius small
- Require explicit acceptance criteria from `roadmap.yaml`
- List tests before coding begins

## Output format

1. Feature summary
2. Acceptance criteria (copy from roadmap + expand)
3. File impact map
4. Test plan
5. Risks and assumptions
6. Done checklist (from `.loop/policies/done-criteria.md`)

## Rules

- Do not start coding in the planner step
- Do not expand scope beyond the feature card
- Escalate ambiguous features to human triage
- Prefer additive changes over invasive refactors
