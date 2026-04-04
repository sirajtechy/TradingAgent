import type { DashboardData, PredictionData, Signal, AgentSummary } from "./types";
import rawDashboard from "../data/dashboard-data.json";
import rawPredictions from "../data/prediction-data.json";

const dashboard = rawDashboard as unknown as DashboardData;
const predictions = rawPredictions as unknown as PredictionData;

export function getDashboardData(): DashboardData {
  return dashboard;
}

export function getPredictionData(): PredictionData {
  return predictions;
}

export function getSignals(): Signal[] {
  return dashboard.signals;
}

export function getAgentSummary(agent: string): AgentSummary | undefined {
  return dashboard.summaries.find((s) => s.agent === agent);
}

export function getAllTickers(): string[] {
  return [...new Set(dashboard.signals.map((s) => s.ticker))].sort();
}

export function getAllMonths(): string[] {
  const months = [...new Set(dashboard.signals.map((s) => s.month))];
  return months.sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
}

export function getAllSectors(): string[] {
  return [...new Set(dashboard.signals.map((s) => s.sector))].sort();
}
