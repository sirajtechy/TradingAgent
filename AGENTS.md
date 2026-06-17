# MyTradingSpace — Agent instructions

This repository uses **loop engineering** ([Addy Osmani](https://addyosmani.com/blog/loop-engineering/)): design systems that discover work, execute in isolation, verify with separate checkers, and persist state on disk — not one-off prompts.

## Before any coding session

1. Read `.loop/policies/done-criteria.md` and `.loop/policies/risk-guardrails.md`
2. Check `.loop/state/queue.json` for selected work
3. Use skills under `.loop/skills/` (feature-planning, trading-architecture, risk-guardrails, testing-standards, mts-cli-ops)
4. Operator journals: `Trading-Journals/DailyCommands.md`, `DailyTradingJournal.md`

## Two loops

| Loop | Purpose | Entry |
|------|---------|--------|
| **Feature loop** | Build code in worktrees | `./bin/mts loop triage` → `select` → `plan` |
| **Research ops loop** | Daily market intelligence (read-only) | `./bin/mts loop ops --date YYYY-MM-DD` |

## Human boundaries (never automate)

- Merge to `main`
- Live trading / broker writes
- Phoenix or fusion **weight** changes without backtest + quant-risk review
- Final buy/hold/avoid decision (use `agent_breakdown` from `--fusion full`)

## Architecture

- Agents: `agents/`
- Orchestrator: `agents/orchestrator/` (one orchestrator; human decision mode)
- CLI: `./bin/mts`
- Loop control plane: `.loop/`
- Full scaffold doc: `skills/tradingagent-loop-engineering-scaffold.md`

## Sub-agents (roles)

| Agent | Role |
|-------|------|
| Triage | Discover and rank work |
| Planner | Plan only — no code |
| Implementer | Code in worktree only |
| Reviewer | Adversarial checker — not the maker |
| Quant-risk | Block scoring/execution semantic changes |
| Test | pytest + artifacts |
| Docs | README, journals, specs |

## Verify before marking done

```bash
python -m pytest tests/ -q
python scripts/loop_verify.py --feature FEAT-xxx
```
