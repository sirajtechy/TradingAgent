import { DashboardData, Signal, AgentSummary, AgentName, PredictionData } from "./types";
import rawData from "@/app/data/dashboard-data.json";
import rawPredictions from "@/app/data/prediction-data.json";

// Re-export computeMetrics from shared utils
export { computeMetrics } from "./data-utils";

const data = rawData as unknown as DashboardData;
const predictionData = rawPredictions as unknown as PredictionData;

export function getPredictionData(): PredictionData {
  return predictionData;
}

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
