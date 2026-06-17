# Done criteria — verifiable stopping conditions

Inspired by loop `/goal`: a feature is **not done** until all conditions below hold.

## Feature loop (code changes)

1. Every acceptance criterion in `roadmap.yaml` is satisfied
2. `python -m pytest tests/ -q` passes (or scoped test path from plan)
3. Reviewer agent status is `approve` or `approve_with_notes` (never `reject`)
4. Quant-risk agent did not escalate
5. Docs agent updated README or relevant spec/journal
6. `.loop/state/feature-journal.md` records outcome
7. `roadmap.yaml` feature status updated (`done` or `blocked`)
8. Human reviewed diff before merge to main

## Research ops loop (daily runs)

1. Session agents ran or cache is fresh (`context_<date>.json`)
2. `agents_available` logged for sample tickers when `--fusion full` runs
3. Artifacts written under `data/output/research/<date>/` when ops script runs
4. `.loop/state/ops-journal.md` updated with health summary
5. No auto trade decisions — human reads breakdown only

## Verify command (loop_verify.py)

Default verify profile for features:

```text
pytest tests/ -q --tb=no
python scripts/loop_verify.py --feature FEAT-xxx
```

Exit code 0 only when all checks pass.
