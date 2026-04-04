// Types for the dashboard data
export interface Signal {
  ticker: string;
  sector: string;
  agent: "technical" | "fundamental" | "orchestrator";
  month: string;
  signalDate: string;
  resultDate: string;
  startPrice: number;
  endPrice: number;
  returnPct: number;
  actualDirection: "up" | "down";
  rawSignal: string;
  signal: "BUY" | "SELL" | "HOLD";
  correct: boolean | null;
  score: number | null;
  scoreBand: string | null;
  frameworks?: Record<string, number | null>;
  // orchestrator extras
  confidence?: number;
  conflictDetected?: boolean;
  conflictResolution?: string | null;
  techScore?: number;
  fundScore?: number;
  weightTech?: number;
  weightFund?: number;
  // fundamental extras
  dataQuality?: string;
}

export interface ConfusionMatrix {
  buyUp: number;
  buyDown: number;
  sellUp: number;
  sellDown: number;
  holdUp: number;
  holdDown: number;
}

export interface SectorSummary {
  totalPeriods: number;
  totalTrades: number;
  correct: number;
  winRate: number | null;
  buys: number;
  sells: number;
  holds: number;
  cm: ConfusionMatrix;
}

export interface AgentSummary {
  agent: string;
  totalPeriods: number;
  totalTrades: number;
  correct: number;
  incorrect: number;
  winRate: number | null;
  buys: number;
  sells: number;
  holds: number;
  tickers: string[];
  cm: ConfusionMatrix;
  bySector: Record<string, SectorSummary>;
}

export interface DashboardData {
  meta: {
    window: string;
    months: number;
    sectors: string[];
    generated: string;
  };
  summaries: AgentSummary[];
  signals: Signal[];
}

export type AgentName = "technical" | "fundamental" | "orchestrator";

// ─── Live Prediction Types ────────────────────────────────────────────
export interface Prediction {
  ticker: string;
  sector: string;
  date: string;
  signal: "bullish" | "bearish" | "neutral";
  signalLabel: "BUY" | "SELL" | "HOLD";
  orchestratorScore: number;
  confidence: number;
  conflictDetected: boolean;
  conflictResolution: string | null;
  note: string | null;
  techSignal: string | null;
  techScore: number | null;
  techBand: string | null;
  techConfidence: string | null;
  techSubscores: Record<string, number>;
  fundSignal: string | null;
  fundScore: number | null;
  fundBand: string | null;
  fundDataQuality: string | null;
  fundSubscores: Record<string, number>;
  weightTech: number;
  weightFund: number;
}

export interface SectorPredictionSummary {
  bullish: number;
  bearish: number;
  neutral: number;
  dominant: string;
  avgScore: number;
}

export interface PredictionData {
  meta: {
    date: string;
    agents: string;
    totalTickers: number;
    errors: number;
  };
  summary: {
    bullish: number;
    bearish: number;
    neutral: number;
    avgScore: number;
    agreementRate: number;
    conflictCount: number;
  };
  sectorSummaries: Record<string, SectorPredictionSummary>;
  predictions: Prediction[];
  highConfidenceSetups: string[];
}
