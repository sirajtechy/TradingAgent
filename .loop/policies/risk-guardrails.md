# Risk guardrails — loop automation boundaries

## Never auto-approve (human required)

- Live order placement or broker write paths
- Position sizing formula changes
- Phoenix or fusion **weight** changes without backtest evidence
- Removal of safeguards, cooldowns, or kill switches
- Changes to hard filter thresholds without quant-risk sign-off
- `auto_eligible: false` features in roadmap

## Escalate to human when

- Test coverage is weak or fixtures absent
- Lookahead bias or leakage suspected in backtest paths
- Signal semantics change indirectly (envelope mapping, operator verdict)
- yfinance fallback silently replaces paid data in production docs
- Reviewer outputs `reject` or quant-risk flags escalation

## Safe for loop automation (default allow)

- New reporting or export modules
- Config validation and schema cleanup
- Documentation and journal automation
- Test coverage improvements
- Dashboard read-only columns
- CLI flags that do not change scoring logic

## Separation of concerns

- **Feature loop** builds code in worktrees — never merges without human
- **Research ops loop** runs `./bin/mts` read-only — never places trades
- **Trading decision** remains human via `agent_breakdown`
