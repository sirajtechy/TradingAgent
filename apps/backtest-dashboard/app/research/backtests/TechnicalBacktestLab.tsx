"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  AGENT_LABELS,
  AgentMetrics,
  formatIngestedAt,
  ingestDayBucket,
  matchesRunPeriod,
  type RunPeriod,
} from "./AgentMatrixHeatmap";
import {
  BUCKET_COLORS,
  BUCKET_LABELS,
  tickersInBucket,
  type ConfusionBucket,
} from "@/app/lib/confusionBucket";

const TECHNICAL_AGENTS = [
  "phoenix",
  "minervini",
  "moglen",
  "breitstein",
  "mcintosh",
] as const;

type RunItem = {
  run_key: string;
  signal_date: string;
  ingested_at: string;
  run_type: string;
  ticker_count: number;
  sector?: string | null;
  backtest_signal_profile?: string | null;
  technical_only?: boolean;
  backtest_mode?: string | null;
  technical_tp?: number | null;
  technical_fn?: number | null;
};

type RunDetail = {
  run_key: string;
  signal_date: string;
  ingested_at?: string;
  ticker_count: number;
  sector?: string | null;
  backtest_signal_profile?: string | null;
  confusion_matrix?: { cumulative?: { by_agent?: Record<string, AgentMetrics> } };
  tickers?: Record<string, Record<string, unknown>>;
};

const PERIOD_FILTERS: { id: RunPeriod; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "yesterday", label: "Yesterday" },
  { id: "week", label: "7d" },
  { id: "all", label: "All" },
];

const BUCKETS: ConfusionBucket[] = ["TP", "FP", "TN", "FN"];

function isSectorTechnicalRun(r: RunItem): boolean {
  if (r.run_type !== "sector_master") return false;
  if (!r.sector || r.sector === "explicit_tickers") return false;
  return (
    r.technical_only === true ||
    r.backtest_mode === "technical_only" ||
    Boolean(r.backtest_signal_profile)
  );
}

export default function TechnicalBacktestLab() {
  const searchParams = useSearchParams();
  const runFromUrl = searchParams.get("run") ?? "";

  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selectedRunKey, setSelectedRunKey] = useState("");
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [period, setPeriod] = useState<RunPeriod>("today");
  const [sectorFilter, setSectorFilter] = useState<string>("");
  const [signalFilter, setSignalFilter] = useState<string>("");
  const [activeAgent, setActiveAgent] = useState<string>("phoenix");
  const [activeBucket, setActiveBucket] = useState<ConfusionBucket>("TP");

  const loadRuns = useCallback(async (sync = false) => {
    setLoading(true);
    setErr(null);
    try {
      const url = sync ? "/api/research/backtests?sync=1" : "/api/research/backtests";
      const r = await fetch(url);
      const d = await r.json();
      if (!d.ok && d.error) throw new Error(d.error);
      setRuns((d.runs ?? []).filter(isSectorTechnicalRun));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load runs");
    } finally {
      setLoading(false);
    }
  }, []);

  const syncRegistry = useCallback(async () => {
    setSyncing(true);
    try {
      await fetch("/api/research/backtests/sync", { method: "POST" });
      await loadRuns(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [loadRuns]);

  useEffect(() => {
    loadRuns(true);
  }, [loadRuns]);

  const sectors = useMemo(() => {
    const s = new Set<string>();
    for (const r of runs) {
      if (r.sector) s.add(r.sector);
    }
    return [...s].sort();
  }, [runs]);

  const filteredRuns = useMemo(
    () =>
      runs
        .filter((r) => matchesRunPeriod(r.ingested_at, period))
        .filter((r) => !sectorFilter || r.sector === sectorFilter)
        .filter((r) => !signalFilter || r.signal_date === signalFilter)
        .sort((a, b) => new Date(b.ingested_at).getTime() - new Date(a.ingested_at).getTime()),
    [runs, period, sectorFilter, signalFilter],
  );

  const signalDates = useMemo(() => {
    const base = sectorFilter
      ? runs.filter((r) => r.sector === sectorFilter)
      : runs;
    return [...new Set(base.map((r) => r.signal_date))].sort().reverse();
  }, [runs, sectorFilter]);

  useEffect(() => {
    if (!filteredRuns.length) {
      setSelectedRunKey("");
      return;
    }
    if (runFromUrl && filteredRuns.some((r) => r.run_key === runFromUrl)) {
      setSelectedRunKey(runFromUrl);
      return;
    }
    if (selectedRunKey && filteredRuns.some((r) => r.run_key === selectedRunKey)) return;
    setSelectedRunKey(filteredRuns[0].run_key);
  }, [filteredRuns, runFromUrl, selectedRunKey]);

  useEffect(() => {
    if (!selectedRunKey) {
      setDetail(null);
      return;
    }
    fetch(`/api/research/backtests/${encodeURIComponent(selectedRunKey)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) throw new Error(d.error);
        setDetail(d.run ?? null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Run load failed"));
  }, [selectedRunKey]);

  const byAgent = detail?.confusion_matrix?.cumulative?.by_agent ?? {};
  const matrixRows = TECHNICAL_AGENTS.filter((id) => id in byAgent).map((id) => ({
    id,
    met: byAgent[id] || {},
  }));

  const bucketTickers = useMemo(() => {
    if (!detail?.tickers || !activeAgent) return [];
    return tickersInBucket(detail.tickers, activeAgent, activeBucket);
  }, [detail?.tickers, activeAgent, activeBucket]);

  const phoenixPilotHref = useMemo(() => {
    if (!selectedRunKey) return "/research/phoenix";
    return `/research/phoenix?rel=${encodeURIComponent(selectedRunKey)}&winners=1`;
  }, [selectedRunKey]);

  const activeMet = byAgent[activeAgent] || {};
  const bucketCount =
    activeBucket === "TP"
      ? activeMet.TP ?? 0
      : activeBucket === "FP"
        ? activeMet.FP ?? 0
        : activeBucket === "TN"
          ? activeMet.TN ?? 0
          : activeMet.FN ?? 0;

  const onCellClick = (agentId: string, bucket: ConfusionBucket, count: number) => {
    if (count <= 0) return;
    setActiveAgent(agentId);
    setActiveBucket(bucket);
  };

  return (
    <div className="p-5 max-w-5xl mx-auto space-y-5">
      <header className="flex flex-wrap items-start gap-3">
        <div>
          <h1 className="text-lg font-semibold text-emerald-300">Technical backtest</h1>
          <p className="text-xs text-[var(--text-dim)] mt-0.5">
            Phoenix + strategies · sector confusion matrix · TP / TN / FP / FN tickers
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={() => syncRegistry()}
            disabled={syncing}
            className="text-xs border border-[var(--border)] rounded px-2.5 py-1.5 hover:bg-white/5 flex items-center gap-1.5"
          >
            <RefreshCw size={12} className={syncing ? "animate-spin" : ""} />
            Sync
          </button>
          <Link
            href={
              selectedRunKey
                ? `/research/backtests/verify?run=${encodeURIComponent(selectedRunKey)}`
                : "/research/backtests/verify"
            }
            className="text-xs border border-cyan-500/30 text-cyan-300 rounded px-2.5 py-1.5 hover:bg-cyan-500/10"
          >
            Polygon verify
          </Link>
          <Link
            href="/research/console"
            className="text-xs border border-emerald-500/30 text-emerald-300 rounded px-2.5 py-1.5 hover:bg-emerald-500/10"
          >
            Run sector
          </Link>
        </div>
      </header>

      {err && <p className="text-xs text-red-400">{err}</p>}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs border border-[var(--border)] rounded-lg px-3 py-2.5 bg-[var(--bg-card)]">
        <span className="text-[var(--text-dim)]">Ran</span>
        {PERIOD_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setPeriod(f.id)}
            className={`rounded px-2 py-0.5 ${
              period === f.id ? "bg-emerald-500/20 text-emerald-300" : "hover:bg-white/5"
            }`}
          >
            {f.label}
          </button>
        ))}
        <span className="text-[var(--text-dim)] ml-2">Sector</span>
        <select
          className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-0.5 max-w-[180px]"
          value={sectorFilter}
          onChange={(e) => {
            setSectorFilter(e.target.value);
            setSignalFilter("");
          }}
        >
          <option value="">All sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <span className="text-[var(--text-dim)]">Signal</span>
        <select
          className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-0.5"
          value={signalFilter}
          onChange={(e) => setSignalFilter(e.target.value)}
        >
          <option value="">Latest</option>
          {signalDates.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        {filteredRuns.length > 1 && (
          <>
            <span className="text-[var(--text-dim)]">Run</span>
            <select
              className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-0.5 min-w-[200px]"
              value={selectedRunKey}
              onChange={(e) => setSelectedRunKey(e.target.value)}
            >
              {filteredRuns.map((r) => (
                <option key={r.run_key} value={r.run_key}>
                  {formatIngestedAt(r.ingested_at)} · {r.signal_date} · {r.ticker_count}tk
                </option>
              ))}
            </select>
          </>
        )}
      </div>

      {loading && <p className="text-xs text-[var(--text-dim)]">Loading…</p>}

      {!loading && !filteredRuns.length && (
        <div className="text-sm text-[var(--text-dim)] border border-[var(--border)] rounded-lg p-6 text-center">
          No sector technical runs for this filter.{" "}
          <Link href="/research/console" className="text-emerald-400 hover:underline">
            Run a sector backtest
          </Link>{" "}
          then Sync.
        </div>
      )}

      {detail && (
        <>
          <div className="text-xs text-[var(--text-dim)] flex flex-wrap gap-x-3 gap-y-1">
            <span>
              <strong className="text-[var(--text)]">{detail.sector}</strong>
            </span>
            <span>signal {detail.signal_date}</span>
            <span>{detail.ticker_count} tickers</span>
            {detail.backtest_signal_profile && <span>{detail.backtest_signal_profile}</span>}
            {detail.ingested_at && <span>ran {formatIngestedAt(detail.ingested_at)}</span>}
          </div>

          {/* Confusion matrix */}
          <div className="border border-[var(--border)] rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--text-dim)] bg-[var(--bg-card)]">
                  <th className="text-left p-2.5 font-normal">Layer</th>
                  {BUCKETS.map((b) => (
                    <th key={b} className="p-2.5 font-normal text-center w-16">
                      {b}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixRows.map(({ id, met }) => (
                  <tr
                    key={id}
                    className={`border-b border-[var(--border)]/50 ${
                      activeAgent === id ? "bg-emerald-500/5" : ""
                    }`}
                  >
                    <td className="p-2.5 font-medium">{AGENT_LABELS[id] || id}</td>
                    {BUCKETS.map((bucket) => {
                      const count =
                        bucket === "TP"
                          ? met.TP ?? 0
                          : bucket === "FP"
                            ? met.FP ?? 0
                            : bucket === "TN"
                              ? met.TN ?? 0
                              : met.FN ?? 0;
                      const selected =
                        activeAgent === id && activeBucket === bucket && count > 0;
                      return (
                        <td key={bucket} className="p-1 text-center">
                          <button
                            type="button"
                            disabled={count === 0}
                            onClick={() => onCellClick(id, bucket, count)}
                            className={`w-full rounded py-1.5 font-mono tabular-nums transition-colors ${
                              count === 0
                                ? "text-zinc-600 cursor-default"
                                : selected
                                  ? BUCKET_COLORS[bucket]
                                  : "hover:bg-white/[0.06] text-[var(--text)]"
                            }`}
                          >
                            {count}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] text-[var(--text-dim)] px-2.5 py-1.5 border-t border-[var(--border)]">
              Click a count to list tickers. For entry, stop, targets, upside, and 5d/4w extension — open{" "}
              <Link href={phoenixPilotHref} className="text-indigo-300 underline">
                Phoenix BUY &amp; WATCH
              </Link>
              .
            </p>
          </div>

          {/* Ticker breakdown */}
          <section className={`rounded-lg border p-3 ${BUCKET_COLORS[activeBucket]}`}>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <h2 className="text-sm font-medium">
                {BUCKET_LABELS[activeBucket]} · {AGENT_LABELS[activeAgent] || activeAgent}
                <span className="font-mono ml-2 opacity-80">
                  {bucketTickers.length}/{bucketCount}
                </span>
              </h2>
              {bucketTickers.length > 0 && activeBucket === "TP" && (
                <Link
                  href={phoenixPilotHref}
                  className="ml-auto text-xs border border-indigo-400/40 text-indigo-300 rounded px-2.5 py-1 hover:bg-indigo-500/10"
                >
                  Open winners in Phoenix Pilot →
                </Link>
              )}
            </div>
            {bucketTickers.length === 0 ? (
              <p className="text-xs mt-2 opacity-80">
                {bucketCount > 0
                  ? "Re-run this sector backtest to refresh ticker drill-down data."
                  : "No tickers in this cell."}
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {bucketTickers.map((t) => (
                  <span
                    key={t.ticker}
                    className="inline-flex items-center gap-1.5 font-mono text-xs border border-current/25 rounded px-2 py-1 bg-black/20"
                    title={
                      t.targetHit === true
                        ? "Target hit — see Phoenix Pilot for entry/stop/targets"
                        : t.targetHit === false
                          ? "Target missed"
                          : "Unknown"
                    }
                  >
                    <span className="font-semibold">{t.ticker}</span>
                    {t.phoenixDisplay && (
                      <span className="opacity-70 text-[10px]">{t.phoenixDisplay}</span>
                    )}
                    {t.targetHit === true && <span className="text-emerald-400">✓</span>}
                    {t.targetHit === false && activeBucket === "FP" && (
                      <span className="text-orange-300">✗</span>
                    )}
                  </span>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
