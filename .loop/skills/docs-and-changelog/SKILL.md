---
name: docs-and-changelog
description: Update README, Trading-Journals, specs, and loop state when a feature ships.
---

# Docs and Changelog Skill

## Update when feature touches

| Change type | Update |
|-------------|--------|
| CLI flags | `Trading-Journals/DailyCommands.md`, `README.md` |
| Data sources | `docs/specs/FREE_DATA_SOURCES.md`, `.env.example` |
| Orchestrator | `Trading-Journals/DailyTradingJournal.md` |
| Loop itself | `skills/tradingagent-loop-engineering-scaffold.md`, root `AGENTS.md` |

## PR handoff

- Summarize feature in `.loop/state/feature-journal.md`
- Link plan file in `.loop/state/plans/`
- Append reviewer row to `.loop/state/review-log.md`
