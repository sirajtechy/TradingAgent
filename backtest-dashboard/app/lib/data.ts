import { DashboardData, Signal, AgentSummary, AgentName, ConfusionMatrix } from "./types";
import rawData from "@/app/data/dashboard-data.json";

const data = rawData as unknown as DashboardData;

export function getDashboardData(): DashboardData {
  return data;
}

export function getSignals(filters?: {
  agent?: AgentName;
  sector?: string;
  ticker?: string;
  signal?: string;
  correct?: boolean | null;
  month?: string;
}): Signal[] {
  let signals = data.signals;
  if (filters?.agent) signals = signals.filter((s) => s.agent === filters.agent);
  if (filters?.sector) signals = signals.filter((s) => s.sector === filters.sector);
  if (filters?.ticker) signals = signals.filter((s) => s.ticker === filters.ticker);
  if (filters?.signal) signals = signals.filter((s) => s.signal === filters.signal);
  if (filters?.correct !== undefined && filters?.correct !== null)
    signals = signals.filter((s) => s.correct === filters.correct);
  if (filters?.month) signals = signals.filter((s) => s.month === filters.month);
  return signals;
}

export function getAgentSummary(agent: AgentName): AgentSummary | undefined {
  return data.summaries.find((s) => s.agent === agent);
}

export function getAllTickers(): string[] {
  return [...new Set(data.signals.map((s) => s.ticker))].sort();
}

export function getAllMonths(): string[] {
  const months: string[] = [];
  const seen = new Set<string>();
  for (const s of data.signals) {
    if (!seen.has(s.month)) {
      seen.add(s.month);
      months.push(s.month);
    }
  }
  return months;
}

export function computeMetrics(signals: Signal[]) {
  const trades = signals.filter((s) => s.signal !== "HOLD");
  const correct = trades.filter((s) => s.correct === true);
  const incorrect = trades.filter((s) => s.correct === false);
  const buys = signals.filter((s) => s.signal === "BUY");
  const sells = signals.filter((s) => s.signal === "SELL");
  const holds = signals.filter((s) => s.signal === "HOLD");

  const tradeReturns = trades.map((s) =>
    s.signal === "BUY" ? s.returnPct : -s.returnPct
  );

  const winRate = trades.length ? (correct.length / trades.length) * 100 : null;

  let sharpe: number | null = null;
  if (tradeReturns.length >= 2) {
    const mean = tradeReturns.reduce((a, b) => a + b, 0) / tradeReturns.length;
    const variance =
      tradeReturns.reduce((a, b) => a + (b - mean) ** 2, 0) /
      (tradeReturns.length - 1);
    const std = Math.sqrt(variance);
    if (std > 0) sharpe = (mean / std) * Math.sqrt(12);
  }

  let maxDrawdown: number | null = null;
  if (tradeReturns.length) {
    let cum = 0, peak = 0, maxDD = 0;
    for (const r of tradeReturns) {
      cum += r;
      if (cum > peak) peak = cum;
      const dd = peak - cum;
      if (dd > maxDD) maxDD = dd;
    }
    maxDrawdown = maxDD;
  }

  let profitFactor: number | null = null;
  const gains = tradeReturns.filter((r) => r > 0).reduce((a, b) => a + b, 0);
  const losses = Math.abs(tradeReturns.filter((r) => r < 0).reduce((a, b) => a + b, 0));
  if (losses > 0) profitFactor = gains / losses;

  const cm: ConfusionMatrix = {
    buyUp: buys.filter((s) => s.actualDirection === "up").length,
    buyDown: buys.filter((s) => s.actualDirection === "down").length,
    sellUp: sells.filter((s) => s.actualDirection === "up").length,
    sellDown: sells.filter((s) => s.actualDirection === "down").length,
    holdUp: holds.filter((s) => s.actualDirection === "up").length,
    holdDown: holds.filter((s) => s.actualDirection === "down").length,
  };

  return {
    totalPeriods: signals.length,
    totalTrades: trades.length,
    correct: correct.length,
    incorrect: incorrect.length,
    winRate: winRate ? Math.round(winRate * 10) / 10 : null,
    sharpe: sharpe ? Math.round(sharpe * 100) / 100 : null,
    maxDrawdown: maxDrawdown ? Math.round(maxDrawdown * 100) / 100 : null,
    profitFactor: profitFactor ? Math.round(profitFactor * 100) / 100 : null,
    buys: buys.length,
    sells: sells.length,
    holds: holds.length,
    cm,
  };
}
