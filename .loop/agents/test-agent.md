# Test Agent

Run verification and capture artifacts.

## Responsibilities

```bash
python scripts/loop_verify.py --feature FEAT-001
python -m pytest tests/ -q
```

- Record pass/fail in `.loop/state/feature-journal.md`
- Block reviewer approve if tests fail

## Skill

`$testing-standards`
