"use client";

import { useMemo } from "react";

export type AgentMetrics = {
  TP?: number;
  FP?: number;
  TN?: number;
  FN?: number;
  neutral?: number;
  neutral_count?: number;
  directional?: number;
  accuracy_pct?: number | null;
  precision_pct?: number | null;
  recall_pct?: number | null;
  f1_pct?: number | null;
  mcc?: number | null;
};

const AGENT_ORDER = [
  "technical",
  "phoenix",
  "fundamental",
  "minervini",
  "moglen",
  "breitstein",
  "mcintosh",
  "fusion",
  "macro",
  "news",
  "insider",
  "sentiment",
  "geopolitics",
  "fusion_full",
];

export const AGENT_LABELS: Record<string, string> = {
  technical: "Technical",
  phoenix: "Phoenix",
  fundamental: "Fundamental",
  minervini: "Minervini",
  moglen: "Moglen",
  breitstein: "Breitstein",
  mcintosh: "McIntosh",
  fusion: "Fusion (CWAF)",
  macro: "Macro",
  news: "News",
  insider: "Insider",
  sentiment: "Sentiment",
  geopolitics: "Geopolitics",
  fusion_full: "Fusion full",
};

function accColor(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return "bg-zinc-800/80 text-zinc-500";
  if (pct >= 70) return "bg-emerald-600/80 text-white";
  if (pct >= 55) return "bg-emerald-500/50 text-emerald-100";
  if (pct >= 45) return "bg-amber-500/40 text-amber-100";
  if (pct >= 30) return "bg-orange-600/50 text-orange-100";
  return "bg-red-700/60 text-red-100";
}

function mccColor(mcc: number | null | undefined): string {
  if (mcc == null || Number.isNaN(mcc)) return "text-zinc-500";
  if (mcc >= 0.3) return "text-emerald-400";
  if (mcc >= 0.1) return "text-amber-300";
  if (mcc >= 0) return "text-orange-300";
  return "text-red-400";
}

export type RunPeriod = "all" | "today" | "yesterday" | "week";

export function ingestDayBucket(iso: string): "today" | "yesterday" | "week" | "older" {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "older";
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday);
  startYesterday.setDate(startYesterday.getDate() - 1);
  const startWeek = new Date(startToday);
  startWeek.setDate(startWeek.getDate() - 7);
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  if (day >= startToday) return "today";
  if (day >= startYesterday) return "yesterday";
  if (day >= startWeek) return "week";
  return "older";
}

export function matchesRunPeriod(iso: string, period: RunPeriod): boolean {
  if (period === "all") return true;
  const bucket = ingestDayBucket(iso);
  if (period === "today") return bucket === "today";
  if (period === "yesterday") return bucket === "yesterday";
  if (period === "week") return bucket === "today" || bucket === "yesterday" || bucket === "week";
  return true;
}

export function formatIngestedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const PERIOD_GROUP_LABELS: Record<string, string> = {
  today: "Today",
  yesterday: "Yesterday",
  week: "Last 7 days",
  older: "Earlier",
};

type HeatmapRunRow = {
  run_key: string;
  signal_date: string;
  ingested_at: string;
  run_type: string;
  sector?: string | null;
  by_agent: Record<string, AgentMetrics>;
};

type ConfusionMetric = "TP" | "FP" | "TN" | "FN" | "accuracy_pct";

const CONFUSION_METRICS: { key: ConfusionMetric; label: string; hint: string }[] = [
  { key: "TP", label: "TP", hint: "True positives" },
  { key: "FP", label: "FP", hint: "False positives" },
  { key: "TN", label: "TN", hint: "True negatives" },
  { key: "FN", label: "FN", hint: "False negatives" },
  { key: "accuracy_pct", label: "Acc %", hint: "Directional accuracy" },
];

function metricCellColor(metric: ConfusionMetric, value: number, max: number): string {
  if (metric === "accuracy_pct") return accColor(value);
  if (value === 0) return "bg-zinc-800/70 text-zinc-500";
  const t = max > 0 ? Math.min(1, value / max) : 0;
  if (metric === "TP") {
    if (t >= 0.7) return "bg-emerald-600/85 text-white";
    if (t >= 0.35) return "bg-emerald-500/45 text-emerald-100";
    return "bg-emerald-900/50 text-emerald-200";
  }
  if (metric === "TN") {
    if (t >= 0.7) return "bg-cyan-700/75 text-white";
    if (t >= 0.35) return "bg-cyan-600/40 text-cyan-100";
    return "bg-cyan-900/45 text-cyan-200";
  }
  if (metric === "FN") {
    if (t >= 0.7) return "bg-red-700/85 text-white";
    if (t >= 0.35) return "bg-red-600/50 text-red-100";
    return "bg-red-900/45 text-red-200";
  }
  if (t >= 0.7) return "bg-orange-700/80 text-white";
  if (t >= 0.35) return "bg-orange-600/45 text-orange-100";
  return "bg-orange-900/45 text-orange-200";
}

function metricValue(met: AgentMetrics, metric: ConfusionMetric): number | null {
  if (metric === "accuracy_pct") return met.accuracy_pct ?? null;
  return (met[metric] as number | undefined) ?? 0;
}

function formatMetricDisplay(metric: ConfusionMetric, value: number | null): string {
  if (value == null) return "—";
  if (metric === "accuracy_pct") return `${value}%`;
  return String(value);
}

export function RegistryConfusionHeatmap({
  runs,
  agents,
  metric,
}: {
  runs: HeatmapRunRow[];
  agents: string[];
  metric: ConfusionMetric;
}) {
  const maxVal = useMemo(() => {
    let max = 0;
    for (const run of runs) {
      for (const aid of agents) {
        const v = metricValue(run.by_agent[aid] || {}, metric);
        if (v != null && metric !== "accuracy_pct" && v > max) max = v;
      }
    }
    return max;
  }, [runs, agents, metric]);

  if (!runs.length) {
    return (
      <div className="text-sm text-[var(--text-dim)] border border-[var(--border)] rounded-lg p-4">
        No runs in this period. Try another filter or sync the registry.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-[var(--border)] rounded-lg">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-[var(--border)] text-[var(--text-dim)]">
            <th className="p-2 text-left sticky left-0 bg-[var(--bg-card)] min-w-[220px]">Run (ingested)</th>
            {agents.map((aid) => (
              <th key={aid} className="p-2 text-center min-w-[4.5rem] whitespace-nowrap">
                {AGENT_LABELS[aid] || aid}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.run_key} className="border-b border-[var(--border)]/40 hover:bg-white/[0.02]">
              <td className="p-2 sticky left-0 bg-[var(--bg-card)]">
                <div className="font-mono text-emerald-300/90">{formatIngestedAt(run.ingested_at)}</div>
                <div className="text-[10px] text-[var(--text-dim)] truncate max-w-[260px]">
                  sig {run.signal_date}
                  {run.sector ? ` · ${run.sector}` : ` · ${run.run_type}`}
                </div>
              </td>
              {agents.map((aid) => {
                const v = metricValue(run.by_agent[aid] || {}, metric);
                return (
                  <td key={aid} className="p-0.5">
                    <div
                      className={`text-center rounded py-1.5 font-mono font-semibold ${metricCellColor(metric, v ?? 0, maxVal)}`}
                      title={`${AGENT_LABELS[aid] || aid}: ${CONFUSION_METRICS.find((m) => m.key === metric)?.hint}`}
                    >
                      {formatMetricDisplay(metric, v)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { PERIOD_GROUP_LABELS, CONFUSION_METRICS };
export type { ConfusionMetric, HeatmapRunRow };

export function orderAgentIds(ids: string[]): string[] {
  return [
    ...AGENT_ORDER.filter((id) => ids.includes(id)),
    ...ids.filter((id) => !AGENT_ORDER.includes(id)).sort(),
  ];
}

export function AgentMatrixHeatmap({
  byAgent,
  compact = false,
  onBucketClick,
}: {
  byAgent: Record<string, AgentMetrics>;
  compact?: boolean;
  onBucketClick?: (agentId: string, bucket: "TP" | "FP" | "TN" | "FN") => void;
}) {
  const rows = useMemo(() => {
    const ids = Object.keys(byAgent);
    const ordered = [
      ...AGENT_ORDER.filter((id) => ids.includes(id)),
      ...ids.filter((id) => !AGENT_ORDER.includes(id)).sort(),
    ];
    return ordered.map((id) => ({ id, met: byAgent[id] || {} }));
  }, [byAgent]);

  if (!rows.length) {
    return (
      <div className="text-sm text-[var(--text-dim)] border border-[var(--border)] rounded-lg p-4">
        No per-agent confusion data yet. Run a labeled backtest with directional signals.
      </div>
    );
  }

  const bucketCell = (
    agentId: string,
    bucket: "TP" | "FP" | "TN" | "FN",
    value: number,
    colorClass: string,
  ) => {
    const clickable = onBucketClick && value > 0;
    const inner = (
      <span
        className={`font-mono ${clickable ? "underline decoration-dotted cursor-pointer hover:opacity-100 opacity-90" : ""} ${colorClass}`}
      >
        {value}
      </span>
    );
    if (!clickable) return inner;
    return (
      <button
        type="button"
        title={`Show ${bucket} tickers for ${AGENT_LABELS[agentId] || agentId}`}
        onClick={() => onBucketClick(agentId, bucket)}
        className="w-full hover:bg-white/[0.06] rounded py-0.5"
      >
        {inner}
      </button>
    );
  };

  return (
    <div className="overflow-x-auto border border-[var(--border)] rounded-lg">
      <table className={`w-full ${compact ? "text-xs" : "text-sm"}`}>
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--text-dim)]">
            <th className="p-2 sticky left-0 bg-[var(--bg-card)]">Agent</th>
            <th className="p-2 text-center" title="Accuracy">
              Acc %
            </th>
            {!compact && (
              <>
                <th className="p-2 text-center">Prec</th>
                <th className="p-2 text-center">Rec</th>
                <th className="p-2 text-center">F1</th>
                <th className="p-2 text-center">MCC</th>
              </>
            )}
            <th className="p-2 text-center text-emerald-400/80">TP</th>
            <th className="p-2 text-center text-red-400/80">FP</th>
            <th className="p-2 text-center text-cyan-400/80">TN</th>
            <th className="p-2 text-center text-amber-400/80">FN</th>
            <th className="p-2 text-center text-zinc-400">Neutral</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ id, met }) => (
            <tr key={id} className="border-b border-[var(--border)]/50 hover:bg-white/[0.02]">
              <td className="p-2 font-medium sticky left-0 bg-[var(--bg-card)]">
                {AGENT_LABELS[id] || id}
              </td>
              <td className="p-1">
                <div
                  className={`text-center rounded px-2 py-1 font-mono font-semibold ${accColor(met.accuracy_pct)}`}
                  title={`Directional: ${met.directional ?? "—"}`}
                >
                  {met.accuracy_pct != null ? `${met.accuracy_pct}%` : "—"}
                </div>
              </td>
              {!compact && (
                <>
                  <td className="p-2 text-center font-mono text-[var(--text-dim)]">
                    {met.precision_pct ?? "—"}
                  </td>
                  <td className="p-2 text-center font-mono text-[var(--text-dim)]">
                    {met.recall_pct ?? "—"}
                  </td>
                  <td className="p-2 text-center font-mono text-[var(--text-dim)]">
                    {met.f1_pct ?? "—"}
                  </td>
                  <td className={`p-2 text-center font-mono ${mccColor(met.mcc)}`}>
                    {met.mcc ?? "—"}
                  </td>
                </>
              )}
              <td className="p-2 text-center">{bucketCell(id, "TP", met.TP ?? 0, "text-emerald-400/90")}</td>
              <td className="p-2 text-center">{bucketCell(id, "FP", met.FP ?? 0, "text-orange-300/90")}</td>
              <td className="p-2 text-center">{bucketCell(id, "TN", met.TN ?? 0, "text-cyan-300/90")}</td>
              <td className="p-2 text-center">{bucketCell(id, "FN", met.FN ?? 0, "text-amber-300/90")}</td>
              <td className="p-2 text-center font-mono text-[var(--text-dim)]">
                {(met.neutral ?? met.neutral_count) ?? 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {onBucketClick && (
        <p className="text-[10px] text-[var(--text-dim)] px-3 py-2 border-t border-[var(--border)]">
          Click any non-zero TP / FP / TN / FN count to list tickers in that bucket.
        </p>
      )}
    </div>
  );
}

export function TimelineAccuracyChart({
  timeline,
  agents = ["technical", "fusion", "fusion_full", "macro"],
}: {
  timeline: Array<{ signal_date: string; agents: Record<string, AgentMetrics> }>;
  agents?: string[];
}) {
  if (!timeline.length) return null;

  return (
    <div className="overflow-x-auto border border-[var(--border)] rounded-lg p-3">
      <div className="text-xs text-[var(--text-dim)] mb-2">Accuracy % by signal date (selected agents)</div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[var(--text-dim)]">
            <th className="text-left p-1 sticky left-0 bg-[var(--bg-card)]">Date</th>
            {agents.map((a) => (
              <th key={a} className="p-1 text-center min-w-[4rem]">
                {AGENT_LABELS[a] || a}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {timeline.map((row) => (
            <tr key={row.signal_date} className="border-t border-[var(--border)]/40">
              <td className="p-1 font-mono sticky left-0 bg-[var(--bg-card)]">{row.signal_date}</td>
              {agents.map((aid) => {
                const acc = row.agents?.[aid]?.accuracy_pct;
                return (
                  <td key={aid} className="p-0.5">
                    <div
                      className={`text-center rounded py-1 font-mono ${accColor(acc ?? null)}`}
                      title={`${aid} @ ${row.signal_date}`}
                    >
                      {acc != null ? acc : "—"}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
