---
name: testing-standards
description: Minimum verification requirements for MyTradingSpace loop-built features.
---

# Testing Standards Skill

## Minimum checks

- Unit tests for new logic under `tests/`
- Integration tests for pipeline or orchestrator wiring when touched
- Fixture-based validation for market/agent JSON shapes when relevant
- `python -m pytest tests/ -q` passes before reviewer approve
- Loop scripts have tests in `tests/test_loop_engine.py`

## Rules

- No feature is done without tests (or documented escalation)
- Bug fixes should include regression tests
- If deterministic validation is impossible, route to human review

## Common commands

```bash
cd MyTradingSpace
python -m pytest tests/ -q
python scripts/loop_verify.py --feature FEAT-001 --dry-run
```
