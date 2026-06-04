---
name: phoenix-only
description: Run Phoenix agent only (no fundamental fusion) for one ticker and as-of date.
metadata:
  openclaw:
    requires:
      bins: ["bash"]
---

# Phoenix only (debug)

Use when the user explicitly wants **Phoenix only**, not fused Phoenix+FA.

```bash
ABS_PATH/openclaw/scripts/orchestrator_analyze.sh \
  --ticker TICKER \
  --date YYYY-MM-DD \
  --fusion phoenix
```

Summarize `phoenix` object from JSON: signal (BUY/WATCH/AVOID), score, report excerpt if useful.
