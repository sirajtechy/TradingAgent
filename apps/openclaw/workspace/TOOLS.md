# Tools — MyTradingSpace orchestrator

## Primary command (phoenix-fa)

Run from repo root. Replace `ABS_PATH` with your `MyTradingSpace` directory.

```bash
ABS_PATH/openclaw/scripts/orchestrator_analyze.sh \
  --ticker TICKER \
  --date YYYY-MM-DD \
  --fusion phoenix-fa
```

Or:

```bash
cd ABS_PATH && .venv/bin/python openclaw/scripts/orchestrator_analyze.py \
  --ticker TICKER --date YYYY-MM-DD --fusion phoenix-fa
```

Stdout is **JSON only**. Do not parse human log lines.

## Environment

Required for live data (set in `~/.openclaw/.env` or shell):

- `POLYGON_API_KEY` — Phoenix / technical OHLCV
- `FMP_API_KEY` — if using `--fund-data-source fmp` (default wrapper uses `yfinance`)

Optional:

- `MYTRADING_PYTHON` — path to venv python if not `ABS_PATH/.venv/bin/python`

## Fusion modes (`--fusion`)

| Value | Use when |
|-------|----------|
| `phoenix-fa` | **Default** — Phoenix + Fundamental + CWAF fusion |
| `phoenix` | Phoenix only (debug) |
| `fundamental` | Fundamental only (debug) |
| `ta-fa` | Legacy TA+FA LangGraph orchestrator (not Phoenix path) |

## Safety

- Ticker: `[A-Z0-9.-]+` only; reject other characters.
- Date: strict `YYYY-MM-DD`.
- Never interpolate user free text into shell; only pass validated ticker/date flags.
