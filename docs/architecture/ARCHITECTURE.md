# MyTradingSpace Architecture

## System Overview

```mermaid
flowchart TB
    subgraph "Control Plane"
        MTS["bin/mts"]
        CLI["cli/__main__.py"]
    end

    subgraph "Pipelines"
        ANALYZE["pipelines/analyze.py"]
        BACKTEST["pipelines/backtest.py"]
        DAILY["pipelines/daily.py"]
    end

    subgraph "Agents"
        PHOENIX["agents/phoenix/"]
        TECH["agents/technical/"]
        FUND["agents/fundamental/"]
        ORCH["agents/orchestrator/"]
        POLY["agents/polygon_data/"]
    end

    subgraph "Core"
        UNIVERSE["core/universe/"]
        CONTRACTS["core/contracts/"]
        IO["core/io/"]
    end

    subgraph "Data Sources"
        POLYGON["Polygon.io API"]
        FMP["FMP API"]
        YFINANCE["YFinance"]
    end

    subgraph "Output"
        JSON["JSON Files"]
        EXCEL["Excel Export"]
        DASHBOARD["Research Lab UI"]
    end

    MTS --> CLI
    CLI --> ANALYZE
    CLI --> BACKTEST
    CLI --> DAILY

    ANALYZE --> PHOENIX
    ANALYZE --> FUND
    ANALYZE --> ORCH

    BACKTEST --> PHOENIX
    BACKTEST --> ORCH

    PHOENIX --> POLY
    TECH --> POLY
    FUND --> FMP
    FUND --> YFINANCE

    POLY --> POLYGON

    ORCH --> PHOENIX
    ORCH --> TECH
    ORCH --> FUND
    ORCH --> CONTRACTS

    IO --> JSON
    IO --> EXCEL
    JSON --> DASHBOARD
```

## Command Flow

```mermaid
flowchart LR
    subgraph "User Commands"
        D["./bin/mts dashboard"]
        A["./bin/mts analyze"]
        S["./bin/mts sector"]
        U["./bin/mts unified"]
        E["./bin/mts export"]
        DY["./bin/mts daily"]
        L["./bin/mts lab"]
    end

    subgraph "CLI Handler"
        CLI["cli/__main__.py"]
    end

    subgraph "Actions"
        NPM["npm run dev"]
        PA["pipelines.analyze"]
        PB["pipelines.backtest"]
        PD["pipelines.daily"]
        EX["core.io.export"]
    end

    D --> CLI --> NPM
    A --> CLI --> PA
    S --> CLI --> PB
    U --> CLI --> PB
    E --> CLI --> EX
    DY --> CLI --> PD
    L --> CLI --> PB
    L --> CLI --> NPM
```

## Agent Architecture

```mermaid
flowchart TB
    subgraph "Agent Registry"
        REG["agents/_registry.py"]
    end

    subgraph "Phoenix Agent"
        PX_SVC["phoenix/service.py"]
        PX_SCORE["phoenix/scoring.py"]
        PX_PATTERN["phoenix/patterns.py"]
        PX_FILTER["phoenix/filters.py"]
        PX_GRAPH["phoenix/graph.py"]
    end

    subgraph "Technical Agent"
        TECH_SVC["technical/service.py"]
        TECH_IND["technical/indicators.py"]
        TECH_RULES["technical/rules.py"]
    end

    subgraph "Fundamental Agent"
        FUND_SVC["fundamental/service.py"]
        FUND_RULES["fundamental/rules.py"]
        FUND_GRAPH["fundamental/graph.py"]
    end

    subgraph "Orchestrator"
        ORCH_SVC["orchestrator/service.py"]
        ORCH_FUSION["orchestrator/fusion.py"]
        ORCH_MODES["orchestrator/modes.py"]
        ORCH_GRAPH["orchestrator/graph.py"]
    end

    REG --> PX_SVC
    REG --> TECH_SVC
    REG --> FUND_SVC

    PX_SVC --> PX_SCORE
    PX_SVC --> PX_PATTERN
    PX_SVC --> PX_FILTER
    PX_SVC --> PX_GRAPH

    TECH_SVC --> TECH_IND
    TECH_SVC --> TECH_RULES

    FUND_SVC --> FUND_RULES
    FUND_SVC --> FUND_GRAPH

    ORCH_SVC --> ORCH_FUSION
    ORCH_SVC --> ORCH_MODES
    ORCH_SVC --> ORCH_GRAPH

    ORCH_FUSION --> PX_SVC
    ORCH_FUSION --> FUND_SVC
    ORCH_FUSION --> TECH_SVC
```

## Fusion Modes

```mermaid
flowchart TB
    subgraph "Fusion Modes"
        PFA["phoenix-fa (default)"]
        PX["phoenix"]
        TFA["ta-fa"]
        FND["fundamental"]
    end

    subgraph "Phoenix+FA Flow"
        PFA --> PX_RUN["Run Phoenix Agent"]
        PFA --> FD_RUN["Run Fundamental Agent"]
        PX_RUN --> FUSE_PFA["fuse_by_mode(PHOENIX_FUND)"]
        FD_RUN --> FUSE_PFA
        FUSE_PFA --> |"90% Phoenix / 10% Fund"| RESULT_PFA["Fusion Result"]
    end

    subgraph "TA+FA Flow"
        TFA --> TECH_RUN["Run Technical Agent"]
        TFA --> FD_RUN2["Run Fundamental Agent"]
        TECH_RUN --> FUSE_TFA["fuse_by_mode(TECH_FUND)"]
        FD_RUN2 --> FUSE_TFA
        FUSE_TFA --> |"CWAF Weights"| RESULT_TFA["Fusion Result"]
    end

    subgraph "Phoenix Only"
        PX --> PX_ONLY["Run Phoenix Agent"]
        PX_ONLY --> RESULT_PX["Phoenix Result"]
    end

    subgraph "Fundamental Only"
        FND --> FD_ONLY["Run Fundamental Agent"]
        FD_ONLY --> RESULT_FND["Fundamental Result"]
    end
```

## Data Flow

```mermaid
flowchart LR
    subgraph "Input"
        TICKER["Ticker Symbol"]
        DATE["As-of Date"]
        MODE["Fusion Mode"]
    end

    subgraph "Data Fetch"
        POLY_API["Polygon API"]
        FMP_API["FMP API"]
        YF_API["YFinance"]
    end

    subgraph "Processing"
        ANALYZE["analyze_single()"]
        SCORE["Agent Scoring"]
        FUSE["Fusion Logic"]
    end

    subgraph "Output"
        JSON_OUT["JSON Result"]
        MASTER["master_pilot.json"]
        BUNDLE["run_bundle.json"]
        XLSX["Excel Export"]
    end

    TICKER --> ANALYZE
    DATE --> ANALYZE
    MODE --> ANALYZE

    ANALYZE --> POLY_API
    ANALYZE --> FMP_API
    ANALYZE --> YF_API

    POLY_API --> SCORE
    FMP_API --> SCORE
    YF_API --> SCORE

    SCORE --> FUSE
    FUSE --> JSON_OUT

    JSON_OUT --> MASTER
    JSON_OUT --> BUNDLE
    MASTER --> XLSX
```

## Backtest Pipeline

```mermaid
flowchart TB
    subgraph "Input"
        SECTOR["Sector Name"]
        DATE["Signal Date"]
        EVAL["Eval Days"]
    end

    subgraph "Universe"
        HALAL["HALAL_SECTORS"]
        TICKERS["Ticker List"]
    end

    subgraph "Parallel Processing"
        WORKER1["Worker 1"]
        WORKER2["Worker 2"]
        WORKERN["Worker N"]
    end

    subgraph "Per-Ticker Analysis"
        FETCH["Fetch Data"]
        PHOENIX["Phoenix Analysis"]
        BACKTEST["Backtest Evaluation"]
    end

    subgraph "Aggregation"
        MERGE["Merge Results"]
        CONFUSION["Confusion Matrix"]
        PILOT["master_pilot.json"]
    end

    SECTOR --> HALAL
    DATE --> HALAL
    HALAL --> TICKERS

    TICKERS --> WORKER1
    TICKERS --> WORKER2
    TICKERS --> WORKERN

    WORKER1 --> FETCH
    WORKER2 --> FETCH
    WORKERN --> FETCH

    FETCH --> PHOENIX
    PHOENIX --> BACKTEST
    BACKTEST --> MERGE

    MERGE --> CONFUSION
    MERGE --> PILOT
```

## Dashboard Architecture

```mermaid
flowchart TB
    subgraph "Next.js App"
        LAYOUT["app/layout.tsx"]
        HOME["app/page.tsx"]
        RESEARCH["app/research/"]
    end

    subgraph "Research Lab"
        SIGNALS["signals/page.tsx"]
        PHOENIX_UI["phoenix/page.tsx"]
        RUNS["runs/page.tsx"]
        SCANS["scans/page.tsx"]
    end

    subgraph "API Routes"
        API_SIGNALS["api/research/signals"]
        API_RUNS["api/trading-runs"]
        API_BUNDLE["api/trading-runs/bundle"]
    end

    subgraph "Data Files"
        JSON_FILES["data/output/trading_runs/"]
        RECONCILED["phoenix_signals_reconciled.json"]
    end

    LAYOUT --> HOME
    LAYOUT --> RESEARCH

    RESEARCH --> SIGNALS
    RESEARCH --> PHOENIX_UI
    RESEARCH --> RUNS
    RESEARCH --> SCANS

    SIGNALS --> API_SIGNALS
    PHOENIX_UI --> API_BUNDLE
    RUNS --> API_RUNS

    API_SIGNALS --> RECONCILED
    API_RUNS --> JSON_FILES
    API_BUNDLE --> JSON_FILES
```

## Export Flow

```mermaid
flowchart TB
    subgraph "Input"
        FROM["--from date"]
        TO["--to date"]
        SIGS["--signals BUY,WATCH"]
    end

    subgraph "Source Discovery"
        ACTIVE["data/output/trading_runs/"]
        ARCHIVE["data/archive/trading_runs/"]
    end

    subgraph "Processing"
        SCAN["Scan master_pilot.json files"]
        DEDUP["Dedupe by (date, ticker)"]
        PRIORITY["Apply source priority"]
    end

    subgraph "Output"
        XLSX["phoenix_signals_reconciled.xlsx"]
        JSON["phoenix_signals_reconciled.json"]
    end

    FROM --> SCAN
    TO --> SCAN
    SIGS --> SCAN

    ACTIVE --> SCAN
    ARCHIVE --> SCAN

    SCAN --> DEDUP
    DEDUP --> PRIORITY

    PRIORITY --> XLSX
    PRIORITY --> JSON
```

## File Structure

```mermaid
graph TD
    ROOT["MyTradingSpace/"]
    
    ROOT --> BIN["bin/mts"]
    ROOT --> CLI["cli/"]
    ROOT --> PIPE["pipelines/"]
    ROOT --> AGENTS["agents/"]
    ROOT --> CORE["core/"]
    ROOT --> APPS["apps/"]
    ROOT --> DATA["data/"]
    ROOT --> DOCS["docs/"]
    
    CLI --> CLI_MAIN["__main__.py"]
    
    PIPE --> P_ANALYZE["analyze.py"]
    PIPE --> P_BACKTEST["backtest.py"]
    PIPE --> P_DAILY["daily.py"]
    
    AGENTS --> A_PHOENIX["phoenix/"]
    AGENTS --> A_TECH["technical/"]
    AGENTS --> A_FUND["fundamental/"]
    AGENTS --> A_ORCH["orchestrator/"]
    AGENTS --> A_POLY["polygon_data/"]
    AGENTS --> A_REG["_registry.py"]
    
    CORE --> C_UNIVERSE["universe/"]
    CORE --> C_DATA["data/"]
    CORE --> C_IO["io/"]
    CORE --> C_CONTRACTS["contracts/"]
    
    APPS --> DASHBOARD["backtest-dashboard/"]
    APPS --> OPENCLAW["openclaw/"]
    
    DATA --> D_INPUT["input/"]
    DATA --> D_OUTPUT["output/"]
```
