---
name: mts-cli-ops
description: Run MyTradingSpace production research commands for the ops loop. Read-only — no auto trade decisions.
---

# MTS CLI Ops Skill

## Daily research sequence

```bash
cd MyTradingSpace
set -a && source .env && set +a

./bin/mts context --date YYYY-MM-DD
./bin/mts daily --date YYYY-MM-DD
./bin/mts analyze --ticker TICKER --fusion full --date YYYY-MM-DD
```

## Health checks

- Session cache: `data/output/context/context_<date>.json`
- All 8 agents in `agent_breakdown`
- `data_sources` per agent documented in output

## Ops loop script

```bash
python scripts/loop_ops_run.py --date YYYY-MM-DD --dry-run
python scripts/loop_ops_run.py --date YYYY-MM-DD
```

## Human decision

- `agent_breakdown` is the deliverable
- `fusion.advisory_verdict` is reference only
