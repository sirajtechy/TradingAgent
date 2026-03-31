# Fundamental Analysis Agent

This project provides a deterministic fundamental analysis agent for a single ticker.

The implementation is intentionally structured in two layers:

- A pure scoring core that does not depend on an LLM.
- A thin LangGraph orchestration layer so the agent can be reused inside larger multi-agent systems.

## What it does

Given a ticker and an optional `as_of_date`, the agent:

- fetches point-in-time-ish financial inputs from Financial Modeling Prep stable endpoints
- evaluates Piotroski, Altman, Graham, Greenblatt, Lynch, growth, and Shariah screens
- returns a deterministic JSON result
- renders a text report for quick reading
- computes an `experimental_score` for backtesting use

## Important limitations

- The score is labeled experimental on purpose. It is designed for backtesting, not as a proven live trading signal.
- Historical profile metadata like sector and industry are taken from the current profile endpoint because FMP does not expose a historical profile snapshot in this implementation.
- The Shariah `impure_revenue_proxy_ratio` uses `interestIncome / revenue` as a proxy. It is not a full business-segmentation purity model.
- Forward analyst estimates are not used in the Lynch calculation because that would weaken point-in-time reproducibility.

## Required environment variable

Set your FMP API key before running the CLI:

```bash
export FMP_API_KEY=your_key_here
```

## CLI usage

```bash
fundamental-agent AAPL
fundamental-agent AAPL --as-of-date 2026-03-28 --format json
fundamental-agent NVDA --as-of-date 2025-12-31 --shariah-standard djim
```

## Output shape

The result includes:

- request metadata
- company snapshot
- raw snapshot values used for scoring
- per-framework calculations and notes
- experimental composite score
- text report

## Project structure

- `fundamental_agent/fmp_client.py`: FMP stable endpoint client and point-in-time snapshot builder
- `fundamental_agent/rules.py`: deterministic framework logic
- `fundamental_agent/graph.py`: LangGraph orchestration
- `fundamental_agent/service.py`: high-level entrypoint for other agents or apps
- `fundamental_agent/cli.py`: command-line interface
