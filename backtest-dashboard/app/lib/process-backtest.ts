/**
 * Process raw backtest JSON files into dashboard-ready data.
 * TypeScript equivalent of scripts/dashboard/_export_dashboard_data.py
 */
import {
  Signal,
  AgentName,
  AgentSummary,
  ConfusionMatrix,
  DashboardData,
  SectorSummary,
} from "./types";

/* ── Sector / Ticker map ─────────────────────────────────── */

const SECTORS: Record<string, string[]> = {
  Technology: ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "ORCL", "ANET", "CRM"],
  Healthcare: ["JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "BMY", "CVS", "CI", "ABT"],
  Financials: ["JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "BLK", "C"],
  Consumer_Staples: ["PEP", "KO", "PG", "WMT", "COST", "MCD", "PM", "MO", "GIS", "CL"],
  Energy: ["XOM", "CVX", "COP", "SLB", "OXY", "PSX", "VLO", "MPC", "EOG", "HAL"],
};

const TICKER_SEC: Record<string, string> = {};
for (const [sec, tickers] of Object.entries(SECTORS)) {
  for (const t of tickers) TICKER_SEC[t] = sec;
}

const SIG_MAP: Record<string, "BUY" | "SELL" | "HOLD"> = {
  bullish: "BUY",
  bearish: "SELL",
  neutral: "HOLD",
};

/* ── Types for raw backtest JSON ─────────────────────────── */

interface RawPeriod {
  month?: string;
  signal_date?: string;
  result_date?: string;
  start_price?: number;
  end_price?: number;
  price_return_pct?: number;
  actual_direction?: string;
  signal?: string;
  signal_correct?: boolean | null;
  experimental_score?: number;
  orchestrator_score?: number;
  score_band?: string;
  frameworks?: Record<string, { applicable?: boolean; score_pct?: number }>;
  confidence?: number;
  conflict_detected?: boolean;
  conflict_resolution?: string | null;
  tech_score?: number;
  fund_score?: number;
  weights_applied?: { tech?: number; fund?: number };
  data_quality?: string;
  error?: string;
}

interface RawTickerData {
  ticker: string;
  periods: RawPeriod[];
  summary?: Record<string, unknown>;
}

export interface UploadedFile {
  name: string;
  data: RawTickerData;
}

/* ── Detect agent type from filename ─────────────────────── */

export function detectAgent(filename: string): AgentName | null {
  const lower = filename.toLowerCase();
  if (lower.includes("orchestrator")) return "orchestrator";
  if (lower.includes("technical")) return "technical";
  if (lower.includes("fundamental") || lower.includes("backtest_results")) return "fundamental";
  return null;
}

/* ── Detect ticker from filename ─────────────────────────── */

export function detectTicker(filename: string): string | null {
  // Try to find a ticker prefix: AAPL_technical_backtest_results.json
  const match = filename.match(/^([A-Z]{1,5})_/);
  return match ? match[1] : null;
}

/* ── Extract signals from raw ticker data ────────────────── */

function extractSignals(
  ticker: string,
  data: RawTickerData,
  agent: AgentName
): Signal[] {
  const sector = TICKER_SEC[ticker] || "Unknown";
  const signals: Signal[] = [];

  for (const p of data.periods) {
    const rawSig = p.signal || "neutral";
    const score =
      agent === "orchestrator"
        ? p.orchestrator_score ?? null
        : p.experimental_score ?? null;

    const s: Signal = {
      ticker,
      sector,
      agent,
      month: p.month || "",
      signalDate: p.signal_date || "",
      resultDate: p.result_date || "",
      startPrice: p.start_price || 0,
      endPrice: p.end_price || 0,
      returnPct: p.price_return_pct || 0,
      actualDirection: (p.actual_direction as "up" | "down") || "up",
      rawSignal: rawSig,
      signal: SIG_MAP[rawSig] || "HOLD",
      correct: p.signal_correct ?? null,
      score,
      scoreBand: p.score_band || null,
    };

    // Frameworks
    if (p.frameworks) {
      s.frameworks = {};
      for (const [k, v] of Object.entries(p.frameworks)) {
        if (v && typeof v === "object" && v.applicable) {
          s.frameworks[k] = v.score_pct ?? null;
        }
      }
    }

    // Orchestrator extras
    if (agent === "orchestrator") {
      s.confidence = p.confidence;
      s.conflictDetected = p.conflict_detected;
      s.conflictResolution = p.conflict_resolution;
      s.techScore = p.tech_score;
      s.fundScore = p.fund_score;
      if (p.weights_applied) {
        s.weightTech = p.weights_applied.tech;
        s.weightFund = p.weights_applied.fund;
      }
    }

    // Fundamental extras
    if (agent === "fundamental") {
      s.dataQuality = p.data_quality;
    }

    signals.push(s);
  }

  return signals;
}

/* ── Confusion matrix from signals ───────────────────────── */

function buildCM(signals: Signal[]): ConfusionMatrix {
  const buys = signals.filter((s) => s.signal === "BUY");
  const sells = signals.filter((s) => s.signal === "SELL");
  const holds = signals.filter((s) => s.signal === "HOLD");
  return {
    buyUp: buys.filter((s) => s.actualDirection === "up").length,
    buyDown: buys.filter((s) => s.actualDirection === "down").length,
    sellUp: sells.filter((s) => s.actualDirection === "up").length,
    sellDown: sells.filter((s) => s.actualDirection === "down").length,
    holdUp: holds.filter((s) => s.actualDirection === "up").length,
    holdDown: holds.filter((s) => s.actualDirection === "down").length,
  };
}

/* ── Agent summary ───────────────────────────────────────── */

function agentSummary(signals: Signal[], agentName: AgentName): AgentSummary {
  const ag = signals.filter((s) => s.agent === agentName);
  const trades = ag.filter((s) => s.signal !== "HOLD");
  const correct = trades.filter((s) => s.correct === true);
  const incorrect = trades.filter((s) => s.correct === false);
  const buys = ag.filter((s) => s.signal === "BUY");
  const sells = ag.filter((s) => s.signal === "SELL");
  const holds = ag.filter((s) => s.signal === "HOLD");
  const winRate = trades.length
    ? Math.round((correct.length / trades.length) * 1000) / 10
    : null;

  // Discover sectors dynamically from the signals
  const sectorSet = new Set(ag.map((s) => s.sector));
  const bySector: Record<string, SectorSummary> = {};

  for (const sec of sectorSet) {
    const secSigs = ag.filter((s) => s.sector === sec);
    const secTrades = secSigs.filter((s) => s.signal !== "HOLD");
    const secCorrect = secTrades.filter((s) => s.correct === true);

    bySector[sec] = {
      totalPeriods: secSigs.length,
      totalTrades: secTrades.length,
      correct: secCorrect.length,
      winRate: secTrades.length
        ? Math.round((secCorrect.length / secTrades.length) * 1000) / 10
        : null,
      buys: secSigs.filter((s) => s.signal === "BUY").length,
      sells: secSigs.filter((s) => s.signal === "SELL").length,
      holds: secSigs.filter((s) => s.signal === "HOLD").length,
      cm: buildCM(secSigs),
    };
  }

  return {
    agent: agentName,
    totalPeriods: ag.length,
    totalTrades: trades.length,
    correct: correct.length,
    incorrect: incorrect.length,
    winRate,
    buys: buys.length,
    sells: sells.length,
    holds: holds.length,
    tickers: [...new Set(ag.map((s) => s.ticker))].sort(),
    cm: buildCM(ag),
    bySector,
  };
}

/* ── Main: process uploaded files → DashboardData ────────── */

export function processBacktestFiles(files: UploadedFile[]): DashboardData {
  const allSignals: Signal[] = [];

  for (const file of files) {
    const agent = detectAgent(file.name);
    if (!agent) continue;
    const ticker = file.data.ticker || detectTicker(file.name) || "UNKNOWN";
    allSignals.push(...extractSignals(ticker, file.data, agent));
  }

  // Discover which agents are present
  const agentSet = new Set(allSignals.map((s) => s.agent));
  const summaries: AgentSummary[] = [];
  for (const a of ["technical", "fundamental", "orchestrator"] as AgentName[]) {
    if (agentSet.has(a)) summaries.push(agentSummary(allSignals, a));
  }

  // Discover sectors and months
  const sectors = [...new Set(allSignals.map((s) => s.sector))].sort();
  const months = new Set(allSignals.map((s) => s.month));
  const monthRange =
    allSignals.length > 0
      ? `${allSignals[0].month} – ${[...months].pop()}`
      : "No data";

  return {
    meta: {
      window: monthRange,
      months: months.size,
      sectors,
      generated: new Date().toISOString().split("T")[0],
    },
    summaries,
    signals: allSignals,
  };
}
