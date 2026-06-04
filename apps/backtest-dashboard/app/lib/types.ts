// ─── Agent Types ──────────────────────────────────────────────────────
export type AgentName = "technical" | "fundamental" | "orchestrator" | "prediction";
export type SignalLabel = "BUY" | "SELL" | "HOLD";
export type RawSignal = "bullish" | "bearish" | "neutral";
export type Direction = "up" | "down";
export type ScoreBand = "strong" | "good" | "mixed_positive" | "mixed" | "weak";

// ─── Per-Period Backtest Signal ──────────────────────────────────────
export interface Signal {
  ticker: string;
  sector: string;
  agent: AgentName;
  month: string;
  signalDate: string;
  resultDate: string;
  startPrice: number;
  endPrice: number;
  returnPct: number;
  actualDirection: Direction;
  rawSignal: string;
  signal: SignalLabel;
  correct: boolean | null;
  score: number | null;
  scoreBand: ScoreBand | null;
  frameworks?: Record<string, number | null>;
  // Patterns detected
  patterns?: { name: string; direction: string; confidence: number }[];
  // Orchestrator
  confidence?: number;
  conflictDetected?: boolean;
  conflictResolution?: string | null;
  techScore?: number;
  fundScore?: number;
  weightTech?: number;
  weightFund?: number;
  // Fundamental
  dataQuality?: string;
  // Trade setup
  entryPrice?: number;
  targetPrice?: number;
  stopLoss?: number;
  entryDate?: string;
  exitDateEst?: string;
  expectedProfitPct?: number;
  riskPct?: number;
  rewardRiskRatio?: number | null;
  confidenceScore?: number;
  profitProbability?: number;
  direction?: string;
  tradeDurationDays?: number;
}

// ─── Confusion Matrix ────────────────────────────────────────────────
export interface ConfusionMatrix {
  buyUp: number;
  buyDown: number;
  sellUp: number;
  sellDown: number;
  holdUp: number;
  holdDown: number;
}

// ─── Sector / Agent Summaries ────────────────────────────────────────
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

// ─── Dashboard Data ──────────────────────────────────────────────────
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

// ─── Prediction Types ────────────────────────────────────────────────
export interface Prediction {
  ticker: string;
  sector: string;
  date: string;
  entryDate: string | null;
  exitDate: string | null;
  holdingDays: number | null;
  signal: RawSignal;
  signalLabel: SignalLabel;
  sentiment: RawSignal;
  orchestratorScore: number;
  confidence: number;
  conviction: string;
  targetPrice: number | null;
  lastPrice: number | null;
  profitPct: number | null;
  peakReturnPct: number | null;
  targetHitProbPct: number | null;
  maxDrawdownPct: number | null;
  winRatePct: number | null;
  seasonalMatch: boolean;
  conflictDetected: boolean;
  conflictResolution: string | null;
  note: string | null;
  techSubscores: Record<string, number>;
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
  meta: { date: string; agents: string; totalTickers: number; errors: number };
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

// ─── Strategy / Prediction Backtest ──────────────────────────────────
export interface StrategyResult {
  strategy: string;
  signal: SignalLabel;
  strength: number;
  correct: boolean | null;
}

export interface PredictionPeriod {
  ticker: string;
  signal_date: string;
  result_date: string;
  entry_price: number;
  end_price: number;
  return_pct: number;
  actual_direction: string;
  predicted_direction: string;
  correct: boolean;
  confluence_score: number;
  confluence_grade: string;
  strategy_results: StrategyResult[];
  target_price: number;
  stop_loss: number;
  risk_reward: number;
}

// ─── Filter State ────────────────────────────────────────────────────
export interface FilterState {
  agents: AgentName[];
  sectors: string[];
  signals: SignalLabel[];
  correctness: "all" | "correct" | "incorrect" | "abstained";
  ticker: string;
  month: string;
  scoreBand: string;
}
