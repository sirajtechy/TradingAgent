---
name: fundamental-only
description: Run Fundamental agent only for one ticker and as-of date.
metadata:
  openclaw:
    requires:
      bins: ["bash"]
---

# Fundamental only (debug)

Use when the user explicitly wants **fundamental analysis only**.

```bash
ABS_PATH/openclaw/scripts/orchestrator_analyze.sh \
  --ticker TICKER \
  --date YYYY-MM-DD \
  --fusion fundamental
```

Summarize `fundamental` from JSON (scores, report, shariah screen if present).

Optional: `--fund-data-source fmp` if user requests FMP instead of default yfinance.
