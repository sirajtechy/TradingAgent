# TradingAgent Loop Engineering Scaffold

This document is a handoff scaffold for implementing a loop-engineering workflow in the `TradingAgent` project, inspired by Addy Osmani’s model of automations, worktrees, skills, connectors, sub-agents, and durable external state.[cite:1]

## Objective

Build a repo-native feature-delivery loop that can:
- discover upcoming engineering work automatically,
- plan and implement bounded features in isolation,
- verify outputs with separate reviewer agents,
- persist progress outside model context,
- and prepare clean handoff artifacts for human approval before merge.[cite:1]

The goal is not fully autonomous trading-system mutation. The goal is controlled acceleration for feature building around the trading platform, with explicit verification gates and durable state.[cite:1]

## Guiding principles

- The human remains responsible for verification; unattended loops can also make unattended mistakes.[cite:1]
- The builder and checker must be separated; the agent that writes code should not be the only agent deciding that the work is complete.[cite:1]
- Durable memory must live in files or external systems, because model context does not persist across runs.[cite:1]
- Work must run in isolated branches or worktrees so concurrent agents do not collide on the same files.[cite:1]
- Start with boring, repeatable, verifiable feature work before letting the loop touch higher-risk trading logic.[cite:1]

## Target outcomes

This loop should help the project produce:
- faster implementation of upcoming features,
- more consistent triage of backlog and technical debt,
- better test and review discipline,
- reusable project instructions for coding agents,
- and cleaner separation between product-engineering automation and live trading decision logic.[cite:1]

## Recommended scope boundary

### Safe for loop automation first

- New analyst or research agents.
- Market data normalization layers.
- Backtest reporting modules.
- Documentation generation.
- Test coverage improvements.
- Config schema cleanup and validation.
- Feature flags and rollout scaffolding.

### Keep human-gated for now

- Live order execution changes.
- Real-money risk parameter changes.
- Core position sizing formulas.
- Broker integration write paths.
- Any production decision rule without deterministic validation.

## Loop design

The loop follows Addy’s six-part model:[cite:1]

| Loop primitive | TradingAgent implementation |
|---|---|
| Automations | Scheduled backlog triage, CI summary, roadmap scan, TODO extraction |
| Worktrees | One worktree per feature task branch |
| Skills | `SKILL.md` files for architecture, risk rules, testing, prompts, repo conventions |
| Connectors | GitHub, issue tracker, CI logs, docs, Slack/Telegram, paper-trading sandbox |
| Sub-agents | Planner, implementer, reviewer, quant-risk checker, test runner, docs writer |
| State | Markdown and YAML/JSON files in `.loop/state/` |

## Proposed repository structure

```text
TradingAgent/
├── .loop/
│   ├── roadmap.yaml
│   ├── policies/
│   │   ├── feature-selection.md
│   │   ├── risk-guardrails.md
│   │   └── done-criteria.md
│   ├── state/
│   │   ├── queue.json
│   │   ├── feature-journal.md
│   │   ├── review-log.md
│   │   └── decisions.md
│   ├── skills/
│   │   ├── feature-planning/
│   │   │   └── SKILL.md
│   │   ├── trading-architecture/
│   │   │   └── SKILL.md
│   │   ├── risk-guardrails/
│   │   │   └── SKILL.md
│   │   ├── testing-standards/
│   │   │   └── SKILL.md
│   │   ├── docs-and-changelog/
│   │   │   └── SKILL.md
│   │   └── prompt-contracts/
│   │       └── SKILL.md
│   ├── agents/
│   │   ├── triage-agent.md
│   │   ├── planner-agent.md
│   │   ├── implementer-agent.md
│   │   ├── reviewer-agent.md
│   │   ├── quant-risk-agent.md
│   │   ├── test-agent.md
│   │   └── docs-agent.md
│   └── templates/
│       ├── feature-card.md
│       ├── implementation-plan.md
│       ├── review-checklist.md
│       └── pr-template.md
├── scripts/
│   ├── loop_triage.py
│   ├── loop_select.py
│   ├── loop_spawn_worktree.sh
│   ├── loop_plan.py
│   ├── loop_verify.py
│   └── loop_update_state.py
└── .github/workflows/
    ├── loop-triage.yml
    ├── loop-feature-build.yml
    └── loop-review-gate.yml
```

## Feature loop lifecycle

```text
Scheduler / manual trigger
  -> Triage backlog and repo signals
  -> Rank candidate tasks
  -> Select one safe bounded feature
  -> Create branch + worktree
  -> Generate implementation plan
  -> Implement in isolation
  -> Run tests and static checks
  -> Run reviewer + risk checker
  -> Update docs and changelog
  -> Open PR / return to backlog / escalate to human
  -> Persist state for next run
```

## Feature selection policy

Only auto-select work items that satisfy all of these:
- clearly scoped,
- limited file blast radius,
- deterministic acceptance criteria,
- testable with existing or easily added fixtures,
- low probability of touching broker execution or capital-risk logic.

A feature should be deferred to human triage if any of these are true:
- requirements are ambiguous,
- it spans many subsystems,
- it changes execution semantics,
- it requires undocumented business judgment,
- or reviewer confidence is low.

## Suggested agent responsibilities

### 1. Triage agent

Responsibilities:
- inspect issues, roadmap, CI failures, TODOs, and recent commits,
- classify work into build now / clarify / human only,
- update `.loop/state/queue.json`,
- and write a short rationale into `feature-journal.md`.[cite:1]

### 2. Planner agent

Responsibilities:
- convert a chosen feature into acceptance criteria,
- identify impacted modules and files,
- list required tests,
- identify dependencies and rollback concerns,
- and produce an implementation plan before coding starts.

### 3. Implementer agent

Responsibilities:
- work only inside the assigned branch or worktree,
- make bounded code changes aligned with the plan,
- avoid unrelated refactors,
- and update local docs/config where required.

### 4. Reviewer agent

Responsibilities:
- validate architecture conformance,
- detect overreach and unintended side effects,
- compare delivered code with plan and acceptance criteria,
- and reject work that passes tests but violates system design intent.[cite:1]

### 5. Quant-risk agent

Responsibilities:
- review for leakage, overfitting shortcuts, unrealistic assumptions, missing guardrails, and bad risk semantics,
- flag suspicious changes around signal weighting, thresholds, ranking logic, or execution transitions,
- and require human review for risk-sensitive areas.

### 6. Test agent

Responsibilities:
- run unit, integration, schema, and smoke checks,
- validate backtest or paper-trade fixtures where relevant,
- collect test output into structured artifacts,
- and update review state as pass/fail.

### 7. Docs agent

Responsibilities:
- update README, feature docs, config references, architecture notes, and changelog,
- summarize the feature for PR handoff,
- and ensure future loops have fresh context.

## Durable state files

### `.loop/roadmap.yaml`

```yaml
epics:
  - id: EPIC-001
    name: Sentiment and macro fusion
    priority: high
    status: active
features:
  - id: FEAT-101
    title: Earnings event analyst
    epic: EPIC-001
    priority: high
    auto_eligible: true
    status: queued
    risk_level: medium
    acceptance_criteria:
      - Emits structured factors
      - Adds fixture-based tests
      - Updates debate graph integration
```

### `.loop/state/queue.json`

```json
{
  "generated_at": "2026-06-10T00:00:00Z",
  "items": [
    {
      "id": "FEAT-101",
      "title": "Earnings event analyst",
      "score": 8.7,
      "status": "candidate",
      "reason": "bounded, testable, aligned with roadmap"
    }
  ]
}
```

### `.loop/state/feature-journal.md`

```md
# Feature Journal

## 2026-06-10
- Selected `FEAT-101` for autonomous build.
- Worktree created: `../wt-feat-101`.
- Planner completed acceptance criteria and file map.
- Reviewer requested tighter fixture coverage before PR.
```

## Skill pack scaffold

Each skill should be explicit, boring, and repo-specific so the agent does not keep guessing project intent.[cite:1]

### `.loop/skills/feature-planning/SKILL.md`

```md
---
name: feature-planning
description: Turn a selected TradingAgent feature into an implementation plan with file scope, acceptance criteria, tests, rollback notes, and PR checklist.
---

# Feature Planning Skill

## Goals
- Produce a bounded implementation plan.
- Keep blast radius small.
- Require explicit acceptance criteria.
- List tests before coding begins.

## Output format
1. Feature summary
2. Acceptance criteria
3. File impact map
4. Test plan
5. Risks and assumptions
6. Done checklist

## Rules
- Do not start coding.
- Do not expand scope.
- Escalate ambiguous features.
- Prefer additive changes over invasive refactors.
```

### `.loop/skills/trading-architecture/SKILL.md`

```md
---
name: trading-architecture
description: Apply repo architecture rules for agents, orchestration, data flow, config boundaries, and module responsibilities.
---

# Trading Architecture Skill

## Principles
- Keep research, signal generation, risk, and execution concerns separated.
- Prefer typed contracts between agents.
- Avoid hidden prompt coupling.
- Keep orchestration deterministic where possible.
- Preserve observability and auditability.

## Review checks
- Did this change blur boundaries between analysis and execution?
- Did it introduce implicit dependencies?
- Did it weaken logging, explainability, or replayability?
```

### `.loop/skills/risk-guardrails/SKILL.md`

```md
---
name: risk-guardrails
description: Enforce risk-sensitive constraints for trading features and block unsafe autonomous changes.
---

# Risk Guardrails Skill

## Never auto-approve
- Live order placement changes
- Position sizing formula changes
- Risk threshold changes
- Broker write-path changes
- Removal of safeguards, cooldowns, or kill switches

## Escalate when
- Test coverage is weak
- Historical fixtures are absent
- Signal confidence is inferred without basis
- Execution behavior changes indirectly
```

### `.loop/skills/testing-standards/SKILL.md`

```md
---
name: testing-standards
description: Define the minimum verification requirements for TradingAgent features.
---

# Testing Standards Skill

## Minimum checks
- Unit tests for new logic
- Integration tests for graph or pipeline wiring
- Fixture-based validation for market/event inputs
- Config/schema validation
- Lint/type checks

## Rules
- No feature is done without tests.
- If a bug fix lacks a regression test, explain why.
- If deterministic validation is impossible, escalate to human review.
```

## Agent prompt scaffold

### `.loop/agents/planner-agent.md`

```md
# Planner Agent

You are the planning agent for TradingAgent.

Your job is to transform a selected feature into a bounded implementation plan.

## Required output
- Feature intent
- Acceptance criteria
- Exact files likely to change
- Tests to add or update
- Risks, assumptions, blockers
- Human escalation notes if ambiguity exists

## Constraints
- Do not code.
- Do not widen scope.
- Do not mark done.
- Prefer minimal invasive changes.
```

### `.loop/agents/implementer-agent.md`

```md
# Implementer Agent

You are the implementation agent for TradingAgent.

## Goal
Deliver the approved feature plan inside the assigned worktree only.

## Constraints
- Change only files justified by the plan.
- Avoid opportunistic refactors.
- Preserve interfaces unless the plan explicitly allows changes.
- Add tests alongside implementation.
- Leave clear notes for reviewer and docs agents.
```

### `.loop/agents/reviewer-agent.md`

```md
# Reviewer Agent

You are the adversarial reviewer for TradingAgent.

## Goal
Disprove that the implementation is ready unless the evidence is strong.

## Checks
- Plan adherence
- Architecture adherence
- Hidden side effects
- Missing tests
- Poor naming or contract clarity
- Weak rollback or migration handling

## Decision output
- approve
- approve_with_notes
- reject
```

### `.loop/agents/quant-risk-agent.md`

```md
# Quant Risk Agent

You are the risk reviewer for TradingAgent.

## Goal
Detect unsafe implications in trading, portfolio, or execution semantics.

## Focus areas
- leakage and lookahead bias
- overfitting shortcuts
- weak assumptions around events or sentiment
- implicit execution changes
- missing guards, clamps, cool-downs, or fail-safe behavior

## Escalation rule
Any uncertain risk-sensitive change must be routed to human review.
```

## GitHub Actions scaffold

### `.github/workflows/loop-triage.yml`

```yaml
name: loop-triage

on:
  schedule:
    - cron: "0 4 * * *"
  workflow_dispatch:

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run loop triage
        run: python scripts/loop_triage.py
      - name: Persist artifacts
        run: |
          git config user.name "loop-bot"
          git config user.email "loop-bot@example.com"
          git add .loop/state/queue.json .loop/state/feature-journal.md || true
          git commit -m "chore(loop): update triage state" || true
```

### `.github/workflows/loop-feature-build.yml`

```yaml
name: loop-feature-build

on:
  workflow_dispatch:
    inputs:
      feature_id:
        description: "Feature ID to build"
        required: true

jobs:
  build_feature:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup worktree branch
        run: bash scripts/loop_spawn_worktree.sh ${{ github.event.inputs.feature_id }}
      - name: Plan feature
        run: python scripts/loop_plan.py --feature ${{ github.event.inputs.feature_id }}
      - name: Implement feature
        run: echo "Invoke coding agent here"
      - name: Verify feature
        run: python scripts/loop_verify.py --feature ${{ github.event.inputs.feature_id }}
```

## Cursor handoff instructions

Use the following handoff prompt in Cursor:

```md
Implement the loop-engineering scaffold for this repository.

Phase 1:
- Create the `.loop/` folder structure exactly as defined.
- Add all scaffold markdown, YAML, JSON, and workflow files.
- Do not yet wire real external APIs.

Phase 2:
- Implement `scripts/loop_triage.py`, `loop_select.py`, `loop_plan.py`, `loop_verify.py`, and `loop_update_state.py` with clean Python structure and TODO-marked integration points.
- Make them runnable in dry-run mode.

Phase 3:
- Add GitHub Actions validation for dry-run execution.
- Add sample feature cards and one example queued feature.

Constraints:
- Preserve separation between research/signal/risk/execution layers.
- Keep live trading paths human-gated.
- Prefer typed models and explicit state files.
- Add tests for the loop scripts.
- Update README with setup instructions.
```

## First feature candidates

Start the loop with one of these feature types:

| Candidate | Why it fits the first loop |
|---|---|
| Earnings event analyst | Bounded, fixture-testable, additive |
| Sentiment normalization pipeline | Clear I/O contracts, low execution risk |
| Backtest summary module | Easy verification, low blast radius |
| Config schema validator | Deterministic, high leverage |
| Docs/changelog automation | Very low risk, good first proof |

## Definition of done

A loop-built feature is only ready for human review when all of the following are true:[cite:1]
- acceptance criteria are satisfied,
- tests and static checks pass,
- reviewer status is not `reject`,
- risk reviewer did not escalate,
- docs are updated,
- and state files reflect the latest outcome.

## Recommended rollout plan

### Phase A: Foundations ✅

- `.loop/` structure, state files, templates, skills, agent specs
- Root `AGENTS.md`, CLI `./bin/mts loop`, GitHub workflows

### Phase B: Dry-run loop ✅

- `scripts/loop_triage.py`, `loop_select.py`, `loop_plan.py`, `loop_verify.py`, `loop_update_state.py`
- Tests in `tests/test_loop_engine.py`

### Phase C: Controlled build mode ✅

- `loop_spawn_worktree.sh`, `loop_run_cycle.sh`, `loop-feature-build.yml`, `loop-review-gate.yml`

### Phase D: Research ops loop ✅

- `scripts/loop_ops_run.py`, `loop-ops-daily.yml`, `ops-journal.md`

### Phase E: Next (human-driven)

- First real loop-built feature (FEAT-001 or FEAT-002)
- Wire implementer agent in worktree; human merge only

## Final note

The loop should replace repetitive prompting, not engineering judgment. The leverage point moves from manual prompting to system design, but verification, comprehension, and responsibility remain human obligations.[cite:1]
