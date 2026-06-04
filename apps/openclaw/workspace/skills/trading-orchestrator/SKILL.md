---
name: trading-orchestrator
description: Run Phoenix+Fundamental fused analysis (phoenix-fa) for a ticker and as-of date via MyTradingSpace wrapper script.
metadata:
  openclaw:
    requires:
      bins: ["bash"]
---

# Trading orchestrator (phoenix-fa)

Use when the user asks to **analyze**, **score**, or **run Phoenix/FA fusion** for a **ticker** and **date**.

## Steps

1. Extract **ticker** (e.g. `AAPL`) and **as-of date** (`YYYY-MM-DD`). If date missing, ask once.
2. Validate ticker is alphanumeric (dots/dashes allowed for symbols like `BRK.B`).
3. Run **exactly** (replace `ABS_PATH` with repo root from Runtime / `repoRoot`):

```bash
ABS_PATH/bin/mts analyze --ticker TICKER --date YYYY-MM-DD --fusion phoenix-fa
```

Legacy wrapper (same backend): `ABS_PATH/openclaw/scripts/orchestrator_analyze.sh …`

4. Parse JSON stdout. If `"ok": false`, report `error`.
5. Summarize for the user:
   - `fusion.final_signal`, `fusion.orchestrator_score`, `fusion.conflict_detected`
   - Phoenix: `phoenix.signal` or `phoenix.phoenix_signal`, score, pattern if present
   - Fundamental: experimental score / signal band if present in `fundamental`

## Defaults

- Fusion: **phoenix-fa** (do not use TA+FA unless user explicitly requests legacy orchestrator).

## Do not

- Shell-interpolate raw user messages into the command.
- Guess scores without running the script.
