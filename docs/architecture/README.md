# Architecture Documentation

Technical documentation for MyTradingSpace system architecture.

## Contents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview with Mermaid diagrams |
| [SCENARIOS.md](./SCENARIOS.md) | Usage scenarios with sequence diagrams |
| [CONFIG.md](./CONFIG.md) | Configuration reference |

## Quick Links

### System Diagrams (ARCHITECTURE.md)

- **System Overview** — High-level component diagram
- **Command Flow** — How CLI commands route to actions
- **Agent Architecture** — Agent registry and internal structure
- **Fusion Modes** — Phoenix+FA vs TA+FA flows
- **Data Flow** — Input → Processing → Output
- **Backtest Pipeline** — Parallel ticker processing
- **Dashboard Architecture** — Next.js routes and APIs
- **Export Flow** — Signal reconciliation and export

### Scenarios (SCENARIOS.md)

1. **Single Ticker Analysis** — `./bin/mts analyze --ticker AAPL`
2. **Sector Backtest** — `./bin/mts sector --sector Energy`
3. **Unified All-Sector** — `./bin/mts unified`
4. **Export Signals** — `./bin/mts export`
5. **Daily Pipeline** — `./bin/mts daily`
6. **Lab Mode** — `./bin/mts lab unified`
7. **Dashboard Browse** — `/research/signals`
8. **Phoenix Pilot Viewer** — `/research/phoenix`

### Configuration (CONFIG.md)

- Environment variables
- CLI command flags
- Fusion modes
- Agent registry
- Output paths
- Dashboard routes
- Scoring thresholds

## Rendering Mermaid

The diagrams use [Mermaid](https://mermaid.js.org/) syntax. To view:

1. **GitHub** — Renders automatically in markdown preview
2. **VS Code** — Install "Mermaid Markdown Syntax Highlighting" extension
3. **Online** — Paste into [mermaid.live](https://mermaid.live/)

## Architecture Principles

1. **Single Entry Point** — All commands via `bin/mts`
2. **Agnostic Pipelines** — `pipelines/` module for all workflows
3. **Agent Isolation** — Each agent is self-contained in `agents/`
4. **Fusion in Orchestrator** — All fusion logic in `agents/orchestrator/`
5. **Core Contracts** — Shared types in `core/contracts/`
6. **Gitignored Outputs** — `data/output/` not committed
