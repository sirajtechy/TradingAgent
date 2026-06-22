/**
 * Confusion bucket classification — mirrors core/universe update_matrix + pilot labels.
 */

export type ConfusionBucket = "TP" | "FP" | "TN" | "FN" | "NEUTRAL" | "UNLABELED";

export type AgentDrilldownSpec = {
  id: string;
  label: string;
  signalKey: string;
  correctKey: string;
  /** Prefer this signal field when present (e.g. directional phoenix). */
  directionalSignalKey?: string;
};

export const AGENT_DRILLDOWN_SPECS: AgentDrilldownSpec[] = [
  {
    id: "technical",
    label: "Technical",
    signalKey: "technical_signal",
    correctKey: "signal_correct_technical",
  },
  {
    id: "phoenix",
    label: "Phoenix",
    signalKey: "phoenix_signal",
    correctKey: "signal_correct_phoenix",
    directionalSignalKey: "phoenix_signal_directional",
  },
  {
    id: "fusion",
    label: "Fusion (CWAF)",
    signalKey: "fusion_final_signal",
    correctKey: "signal_correct",
    directionalSignalKey: "fusion_signal",
  },
  {
    id: "fundamental",
    label: "Fundamental",
    signalKey: "fund_signal_normalized",
    correctKey: "signal_correct_fundamental",
  },
  {
    id: "minervini",
    label: "Minervini",
    signalKey: "minervini_signal",
    correctKey: "signal_correct_minervini",
  },
  {
    id: "moglen",
    label: "Moglen",
    signalKey: "moglen_signal",
    correctKey: "signal_correct_moglen",
  },
  {
    id: "breitstein",
    label: "Breitstein",
    signalKey: "breitstein_signal",
    correctKey: "signal_correct_breitstein",
  },
  {
    id: "mcintosh",
    label: "McIntosh",
    signalKey: "mcintosh_signal",
    correctKey: "signal_correct_mcintosh",
  },
  {
    id: "fusion_full",
    label: "Fusion full",
    signalKey: "fusion_full_signal",
    correctKey: "signal_correct_fusion_full",
  },
  {
    id: "macro",
    label: "Macro",
    signalKey: "macro_signal",
    correctKey: "signal_correct_macro",
  },
  {
    id: "news",
    label: "News",
    signalKey: "news_signal",
    correctKey: "signal_correct_news",
  },
  {
    id: "insider",
    label: "Insider",
    signalKey: "insider_signal",
    correctKey: "signal_correct_insider",
  },
  {
    id: "sentiment",
    label: "Sentiment",
    signalKey: "sentiment_signal",
    correctKey: "signal_correct_sentiment",
  },
  {
    id: "geopolitics",
    label: "Geopolitics",
    signalKey: "geopolitics_signal",
    correctKey: "signal_correct_geopolitics",
  },
];

export function agentDrilldownSpec(agentId: string): AgentDrilldownSpec | undefined {
  return AGENT_DRILLDOWN_SPECS.find((s) => s.id === agentId);
}

function normalizeSignal(raw: string | null | undefined): string {
  const s = (raw || "").trim().toLowerCase();
  if (s === "buy" || s === "watch") return "bullish";
  if (s === "avoid" || s === "sell") return "bearish";
  return s || "neutral";
}

export function signalForAgent(row: Record<string, unknown>, spec: AgentDrilldownSpec): string {
  const dir = spec.directionalSignalKey ? row[spec.directionalSignalKey] : undefined;
  const raw = dir ?? row[spec.signalKey];
  return normalizeSignal(typeof raw === "string" ? raw : undefined);
}

export function confusionBucket(
  fusionFinalSignal: string | null | undefined,
  signalCorrect: boolean | null | undefined,
): ConfusionBucket {
  const sig = normalizeSignal(fusionFinalSignal);
  const sc = signalCorrect;
  if (sc === null || sc === undefined) {
    return sig === "bullish" || sig === "bearish" ? "UNLABELED" : "NEUTRAL";
  }
  if (sig === "bullish") return sc ? "TP" : "FP";
  if (sig === "bearish") return sc ? "TN" : "FN";
  return "NEUTRAL";
}

export function bucketForAgentRow(
  row: Record<string, unknown>,
  agentId: string,
): ConfusionBucket {
  const spec = agentDrilldownSpec(agentId);
  if (!spec) return "UNLABELED";
  const sig = signalForAgent(row, spec);
  const correct = row[spec.correctKey];
  return confusionBucket(sig, correct === null || correct === undefined ? null : Boolean(correct));
}

export type TickerDrilldownRow = {
  ticker: string;
  sector?: string | null;
  signal: string;
  targetHit?: boolean | null;
  correct?: boolean | null;
  phoenixDisplay?: string | null;
  /** Signal date from run manifest (entry assumed at as-of close). */
  entryDate?: string | null;
  entryPrice?: number | null;
  stopPrice?: number | null;
  targetT1?: number | null;
  targetT2?: number | null;
  backtestTargetPrice?: number | null;
  /** @deprecated use backtestTargetPrice / targetT1 */
  targetPrice?: number | null;
  targetHitDate?: string | null;
  exitReferenceDate?: string | null;
  exitPrice?: number | null;
};

function numOrNull(v: unknown): number | null {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return null;
  return Number(v);
}

function strOrNull(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s || null;
}

export function tickersInBucket(
  tickers: Record<string, Record<string, unknown>>,
  agentId: string,
  bucket: ConfusionBucket,
  options?: { signalDate?: string | null },
): TickerDrilldownRow[] {
  const spec = agentDrilldownSpec(agentId);
  if (!spec) return [];

  const out: TickerDrilldownRow[] = [];
  for (const [sym, row] of Object.entries(tickers)) {
    if (bucketForAgentRow(row, agentId) !== bucket) continue;
    const sig = signalForAgent(row, spec);
    const correct = row[spec.correctKey];
    const backtestTarget = numOrNull(row.backtest_target_price);
    out.push({
      ticker: sym,
      sector: row.sector as string | null | undefined,
      signal: sig,
      targetHit: row.target_hit as boolean | null | undefined,
      correct: correct === null || correct === undefined ? null : Boolean(correct),
      phoenixDisplay:
        typeof row.phoenix_signal === "string" ? (row.phoenix_signal as string) : null,
      entryDate: options?.signalDate ?? strOrNull(row.signal_date),
      entryPrice: numOrNull(row.entry_price),
      stopPrice: numOrNull(row.stop_price),
      targetT1: numOrNull(row.target_t1),
      targetT2: numOrNull(row.target_t2),
      backtestTargetPrice: backtestTarget,
      targetPrice: backtestTarget,
      targetHitDate: strOrNull(row.target_hit_date),
      exitReferenceDate: strOrNull(row.exit_reference_date),
      exitPrice: numOrNull(row.exit_price),
    });
  }
  return out.sort((a, b) => a.ticker.localeCompare(b.ticker));
}

export const BUCKET_LABELS: Record<ConfusionBucket, string> = {
  TP: "True positive",
  FP: "False positive",
  TN: "True negative",
  FN: "False negative",
  NEUTRAL: "Neutral / abstain",
  UNLABELED: "Unlabeled",
};

export const BUCKET_COLORS: Record<ConfusionBucket, string> = {
  TP: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  FP: "text-orange-300 border-orange-500/40 bg-orange-500/10",
  TN: "text-cyan-300 border-cyan-500/40 bg-cyan-500/10",
  FN: "text-red-400 border-red-500/40 bg-red-500/10",
  NEUTRAL: "text-zinc-400 border-zinc-500/40 bg-zinc-500/10",
  UNLABELED: "text-zinc-500 border-zinc-600/40 bg-zinc-800/40",
};

export function confusionCells(bucket: ConfusionBucket): {
  TP: string;
  FP: string;
  TN: string;
  FN: string;
} {
  return {
    TP: bucket === "TP" ? "✓" : "",
    FP: bucket === "FP" ? "✓" : "",
    TN: bucket === "TN" ? "✓" : "",
    FN: bucket === "FN" ? "✓" : "",
  };
}
