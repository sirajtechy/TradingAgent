# Usage Scenarios

## Scenario 1: Single Ticker Analysis

**Command:** `./bin/mts analyze --ticker AAPL --date 2026-05-28`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Pipeline as pipelines/analyze
    participant Phoenix as agents/phoenix
    participant Fund as agents/fundamental
    participant Polygon as Polygon API
    participant FMP as FMP API

    User->>CLI: analyze --ticker AAPL
    CLI->>Pipeline: analyze_single(ticker, date, fusion="phoenix-fa")
    
    Pipeline->>Phoenix: analyze_ticker(AAPL, date)
    Phoenix->>Polygon: fetch_daily_bars()
    Polygon-->>Phoenix: OHLCV data
    Phoenix->>Phoenix: detect_patterns()
    Phoenix->>Phoenix: build_score()
    Phoenix-->>Pipeline: phoenix_result
    
    Pipeline->>Fund: analyze_ticker(AAPL, date)
    Fund->>FMP: get_financials()
    FMP-->>Fund: financial data
    Fund->>Fund: evaluate_snapshot()
    Fund-->>Pipeline: fund_result
    
    Pipeline->>Pipeline: fuse_by_mode(PHOENIX_FUND)
    Pipeline-->>CLI: fusion_result JSON
    CLI-->>User: Print JSON
```

## Scenario 2: Sector Backtest

**Command:** `./bin/mts sector --sector Energy --date 2026-05-28`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Pipeline as pipelines/backtest
    participant Universe as core/universe
    participant Worker as ThreadPoolExecutor
    participant Phoenix as agents/phoenix
    participant IO as core/io

    User->>CLI: sector --sector Energy
    CLI->>Pipeline: run_sector_pilot(Energy, date)
    
    Pipeline->>Universe: HALAL_SECTORS["Energy"]
    Universe-->>Pipeline: [XOM, CVX, COP, ...]
    
    Pipeline->>Worker: submit(analyze_ticker) for each
    
    loop For each ticker
        Worker->>Phoenix: analyze_ticker()
        Phoenix-->>Worker: result
        Worker->>Worker: backtest_evaluate()
    end
    
    Worker-->>Pipeline: all_results
    
    Pipeline->>IO: merge_confusion()
    Pipeline->>IO: write master_pilot.json
    
    IO-->>CLI: output_path
    CLI-->>User: "Done: data/output/trading_runs/..."
```

## Scenario 3: Unified All-Sector Backtest

**Command:** `./bin/mts unified --date 2026-05-28`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Pipeline as pipelines/backtest
    participant Universe as core/universe
    participant Worker as ThreadPoolExecutor
    participant IO as core/io

    User->>CLI: unified --date 2026-05-28
    CLI->>Pipeline: run_unified_pilot(date)
    
    Pipeline->>Universe: HALAL_SECTORS.keys()
    Universe-->>Pipeline: [Technology, Healthcare, Energy, ...]
    
    loop For each sector
        Pipeline->>Worker: run_sector_pilot(sector)
        Worker-->>Pipeline: sector_results
    end
    
    Pipeline->>IO: merge_all_sectors()
    Pipeline->>IO: write unified_master_YYYY-MM-DD/master_pilot.json
    
    IO-->>CLI: unified_path
    CLI-->>User: "Unified: 537 tickers, 2 BUY, 113 WATCH"
```

## Scenario 4: Export Signals

**Command:** `./bin/mts export --from 2026-05-10 --to 2026-05-28`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Export as core/io/export
    participant FS as File System

    User->>CLI: export --from 2026-05-10 --to 2026-05-28
    CLI->>Export: export_signals(from, to, signals=["BUY","WATCH"])
    
    Export->>FS: scan data/output/trading_runs/
    FS-->>Export: master_pilot.json files
    
    Export->>FS: scan data/archive/trading_runs/
    FS-->>Export: archived master_pilot.json files
    
    Export->>Export: parse_all_sources()
    Export->>Export: dedupe_by_date_ticker()
    Export->>Export: apply_priority()
    
    Export->>FS: write phoenix_signals_reconciled.xlsx
    Export->>FS: write phoenix_signals_reconciled.json
    
    Export-->>CLI: {sources: 35, signals: 999, BUY: 59, WATCH: 940}
    CLI-->>User: "Excel → .../phoenix_signals_reconciled.xlsx"
```

## Scenario 5: Daily Pipeline

**Command:** `./bin/mts daily`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Daily as pipelines/daily
    participant Backtest as pipelines/backtest
    participant Export as core/io/export
    participant Notify as notify_daily_summary.py

    User->>CLI: daily
    CLI->>Daily: run_daily()
    
    Daily->>Daily: signal_date = today
    Daily->>Backtest: run_unified_pilot(signal_date)
    Backtest-->>Daily: master_pilot_path
    
    Daily->>Export: export_signals(today, today)
    Export-->>Daily: excel_path
    
    alt SEND_TELEGRAM=1
        Daily->>Notify: notify_daily_summary.py
        Notify-->>Daily: telegram sent
    end
    
    Daily-->>CLI: summary
    CLI-->>User: "Daily pipeline complete"
```

## Scenario 6: Lab Mode (Backtest + Dashboard)

**Command:** `./bin/mts lab unified --date 2026-05-28`

```mermaid
sequenceDiagram
    participant User
    participant CLI as bin/mts
    participant Backtest as pipelines/backtest
    participant Dashboard as npm run dev

    User->>CLI: lab unified --date 2026-05-28
    
    CLI->>Backtest: run_unified_pilot(date)
    Backtest-->>CLI: master_pilot_path
    
    CLI->>Dashboard: start on port 3055
    Dashboard-->>CLI: ready
    
    CLI-->>User: "Dashboard: http://localhost:3055"
    CLI-->>User: "Results: data/output/trading_runs/..."
```

## Scenario 7: Dashboard Browse

**User Action:** Open http://localhost:3055/research/signals

```mermaid
sequenceDiagram
    participant Browser
    participant NextJS as Next.js App
    participant API as API Route
    participant FS as File System

    Browser->>NextJS: GET /research/signals
    NextJS->>NextJS: render signals/page.tsx
    
    NextJS->>API: fetch /api/research/signals
    API->>FS: read phoenix_signals_reconciled.json
    FS-->>API: JSON data
    API-->>NextJS: {signals: [...], meta: {...}}
    
    NextJS->>NextJS: render SignalsTable
    NextJS-->>Browser: HTML + hydrated React
    
    Browser->>Browser: User filters by BUY
    Browser->>Browser: Local state update (no API)
```

## Scenario 8: Phoenix Pilot Viewer

**User Action:** Open http://localhost:3055/research/phoenix

```mermaid
sequenceDiagram
    participant Browser
    participant NextJS as Next.js App
    participant API as API Route
    participant FS as File System

    Browser->>NextJS: GET /research/phoenix
    NextJS->>NextJS: render phoenix/page.tsx
    
    NextJS->>API: fetch /api/trading-runs
    API->>FS: scan data/output/trading_runs/
    FS-->>API: [{id, relPath, kind: "master"}, ...]
    API-->>NextJS: runs list
    
    Browser->>Browser: User selects a run
    Browser->>API: fetch /api/trading-runs/bundle?rel=...
    API->>FS: read master_pilot.json
    FS-->>API: pilot data
    API-->>NextJS: tickers map
    
    NextJS->>NextJS: render sortable table
    NextJS-->>Browser: BUY/WATCH rows + Excel export
```
