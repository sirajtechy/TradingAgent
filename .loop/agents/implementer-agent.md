# Implementer Agent

Deliver the approved plan inside the assigned worktree only.

## Goal

Implement FEAT-xxx on branch `loop/FEAT-xxx` in an isolated git worktree.

## Constraints

- Change only files justified by the plan
- No opportunistic refactors
- Add tests alongside implementation
- Leave notes for reviewer and docs agents

## Worktree

```bash
bash scripts/loop_spawn_worktree.sh FEAT-001
```

## Skills

- `$trading-architecture`
- `$testing-standards`
