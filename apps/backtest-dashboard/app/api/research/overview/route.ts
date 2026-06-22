import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";
import { findMasterPilot, loadWatchlistRows, researchDir, tradingRunsDir } from "@/app/lib/masterPilot";

export const dynamic = "force-dynamic";

const AGENT_SOURCES = [
  {
    id: "phoenix",
    label: "Phoenix",
    role: "Pattern/stage TA — BUY / WATCH / AVOID, entry, stop, targets",
    primary: "Polygon OHLCV",
    fallback: "—",
    cli: "./bin/mts daily",
    tier: "primary",
  },
  {
    id: "fundamental",
    label: "Fundamental",
    role: "Shariah + financial score fused with Phoenix (90/10 CWAF)",
    primary: "FMP",
    fallback: "yfinance",
    cli: "./bin/mts daily",
    tier: "primary",
  },
  {
    id: "macro",
    label: "Macro",
    role: "Fed funds, CPI, unemployment, yield curve",
    primary: "FRED",
    fallback: "yfinance (^TNX / ^IRX)",
    cli: "./bin/mts agent macro",
    tier: "primary",
  },
  {
    id: "market_summary",
    label: "Market summary",
    role: "VIX regime, SPY 20d, sector leaders vs SPY",
    primary: "Polygon + FRED",
    fallback: "yfinance VIX",
    cli: "./bin/mts agent market_summary",
    tier: "primary",
  },
  {
    id: "news",
    label: "News",
    role: "Headlines + analyst grades",
    primary: "FMP → Finnhub",
    fallback: "yfinance news",
    cli: "./bin/mts agent news --ticker X",
    tier: "mixed",
  },
  {
    id: "insider",
    label: "Insider",
    role: "Form 4 common-stock sales (code S) — who sold, when, $ volume",
    primary: "SEC EDGAR Form 4",
    fallback: "FMP → yfinance",
    cli: "./bin/mts agent insider --ticker X",
    tier: "primary",
  },
  {
    id: "geopolitics",
    label: "Geopolitics",
    role: "Geo keyword scan on market headlines",
    primary: "FMP general news",
    fallback: "yfinance ETF/news scan",
    cli: "./bin/mts agent geopolitics",
    tier: "fallback",
  },
  {
    id: "sentiment",
    label: "Sentiment",
    role: "Composite of news, insider, macro, geopolitics",
    primary: "Derived (upstream agents)",
    fallback: "—",
    cli: "./bin/mts analyze --fusion full",
    tier: "derived",
  },
];

const SIGNALS_JSON = path.join("data", "output", "trading_runs", "phoenix_signals_reconciled.json");

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const dateParam = url.searchParams.get("date");
    const tradeFocus = url.searchParams.get("trade_focus") === "1";

    const master = findMasterPilot(root, dateParam);
    if (!master) {
      return NextResponse.json(
        {
          ok: false,
          error: "No master_pilot.json found. Run: ./bin/mts daily",
          agents: AGENT_SOURCES,
          pipeline: {
            daily: "./bin/mts daily",
            export: "./bin/mts export",
            analyze_single: "./bin/mts analyze --ticker X --fusion full --export-breakdown --refresh-context",
            analyze_watchlist: "./bin/mts analyze --watchlist --fusion full --export-breakdown --refresh-context",
          },
        },
        { status: 404, headers: { "Cache-Control": "no-store" } },
      );
    }

    const watchlist = loadWatchlistRows(root, master.path, master.signalDate, {
      tradeFocus,
      signals: new Set(["BUY", "WATCH"]),
    });

    const signalsPath = path.join(root, SIGNALS_JSON);
    let signalsExport: Record<string, unknown> = { exists: false, path: SIGNALS_JSON.replace(/\\/g, "/") };
    if (fs.existsSync(signalsPath)) {
      try {
        const sigDoc = JSON.parse(fs.readFileSync(signalsPath, "utf-8"));
        signalsExport = {
          exists: true,
          path: SIGNALS_JSON.replace(/\\/g, "/"),
          buy: sigDoc.summary?.buy ?? sigDoc.buy_count,
          watch: sigDoc.summary?.watch ?? sigDoc.watch_count,
          generated_at: sigDoc.generated_at,
        };
      } catch {
        signalsExport.exists = true;
      }
    }

    const researchIndex = path.join(researchDir(root), master.signalDate, "watchlist_analyze.json");
    const watchlistIndexExists = fs.existsSync(researchIndex);

    const buyRows = watchlist.filter((t) => t.phoenix_signal === "BUY");
    const watchRows = watchlist.filter((t) => t.phoenix_signal === "WATCH");
    const analyzed = watchlist.filter((t) => t.analyze_cached).length;

    return NextResponse.json(
      {
        ok: true,
        as_of_date: master.signalDate,
        master: {
          source_path: path.relative(root, master.path).replace(/\\/g, "/"),
          source_rel: master.rel,
          buy_count: buyRows.length,
          watch_count: watchRows.length,
          total_buy_watch: watchlist.length,
          analyzed_count: analyzed,
          pending_analyze: watchlist.length - analyzed,
        },
        signals_export: signalsExport,
        watchlist_index_exists: watchlistIndexExists,
        agents: AGENT_SOURCES,
        watchlist,
        pipeline: {
          daily: "./bin/mts daily",
          export: "./bin/mts export",
          dashboard: "./bin/mts dashboard -b",
          analyze_single:
            "./bin/mts analyze --ticker TICKER --fusion full --export-breakdown --refresh-context",
          analyze_watchlist:
            "./bin/mts analyze --watchlist --fusion full --export-breakdown --refresh-context",
        },
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Overview load failed" },
      { status: 500 },
    );
  }
}
