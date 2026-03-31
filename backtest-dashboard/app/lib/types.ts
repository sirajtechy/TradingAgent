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
