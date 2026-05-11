"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ChevronDown, GitCompare, Layers } from "lucide-react";
import { confusionBucket, confusionCells } from "../lib/confusionBucket";

type RunItem = { id: string; relPath: string; modified: string; kind?: string };

type Bundle = {
  schema_version?: string;
  run_id?: string;
  as_of_date?: string;
  fusion?: string;
  row_count?: number;
  matrices?: Record<string, unknown>;
  rows?: Array<{
    ticker: string;
    sector?: string | null;
    fusion_final_signal?: string | null;
    fusion_orchestrator_score?: number | null;
    phoenix_signal?: string | null;
    fund_signal_normalized?: string | null;
    fusion_conflict?: boolean | null;
    hard_filter_passed?: boolean | null;
    error?: string | null;
    evaluation?: { signal_correct?: boolean | null; directional_labels_available?: boolean | null };
  }>;
};

type CmpResp = {
  summary: { tickers_compared: number; signal_changes: number; added: number; removed: number };
  per_ticker: Record<string, { status: string; changed?: boolean; fusion_signal?: { from?: string; to?: string } }>;
};

export default function TradingRunsPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [primary, setPrimary] = useState("");
  const [secondary, setSecondary] = useState("");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [comparison, setComparison] = useState<CmpResp | null>(null);
  const [sector, setSector] = useState("All");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/trading-runs")
      .then((r) => r.json())
      .then((d) => setRuns(d.runs ?? []))
      .catch(() => setErr("Failed to list runs"));
  }, []);

  useEffect(() => {
    if (!primary) {
      setBundle(null);
      return;
    }
    const rel = runs.find((x) => x.id === primary)?.relPath;
    if (!rel) return;
    setLoading(true);
    setErr(null);
    fetch(`/api/trading-runs/bundle?rel=${encodeURIComponent(rel)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) throw new Error(d.error);
        setBundle(d);
      })
      .catch((e) => setErr(String(e.message)))
      .finally(() => setLoading(false));
  }, [primary, runs]);

  useEffect(() => {
    if (!primary || !secondary || primary === secondary) {
      setComparison(null);
      return;
    }
    const ra = runs.find((x) => x.id === primary)?.relPath;
    const rb = runs.find((x) => x.id === secondary)?.relPath;
    if (!ra || !rb) return;
    fetch(`/api/trading-runs/compare?a=${encodeURIComponent(ra)}&b=${encodeURIComponent(rb)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) throw new Error(d.error);
        setComparison({ summary: d.summary, per_ticker: d.per_ticker });
      })
      .catch(() => setComparison(null));
  }, [primary, secondary, runs]);

  const sectors = useMemo(() => {
    const s = new Set<string>();
    bundle?.rows?.forEach((r) => {
      if (r.sector) s.add(r.sector);
    });
    return ["All", ...Array.from(s).sort()];
  }, [bundle]);

  const filteredRows = useMemo(() => {
    const rows = bundle?.rows ?? [];
    if (sector === "All") return rows;
    return rows.filter((r) => r.sector === sector);
  }, [bundle, sector]);

  const matrix = bundle?.matrices as Record<string, unknown> | undefined;

  const bundleRuns = useMemo(
    () => runs.filter((r) => r.kind === "bundle" || !r.kind),
    [runs],
  );

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] p-6 max-w-[1400px] mx-auto">
      <div className="flex flex-wrap items-center gap-4 mb-8">
        <Link href="/" className="text-[var(--text-dim)] hover:text-white flex items-center gap-2">
          <ArrowLeft size={18} /> Home
        </Link>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <Layers className="text-indigo-400" size={22} />
          Trading runs (run_bundle.json)
        </h1>
        <Link
          href="/phoenix-watch-buy"
          className="ml-auto text-sm rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-4 py-2 text-indigo-300 hover:bg-indigo-500/20 transition-colors"
        >
          Phoenix BUY &amp; WATCH →
        </Link>
      </div>

      <p className="text-sm text-[var(--text-dim)] mb-6 max-w-3xl">
        Loads aggregated outputs from <code className="text-indigo-300">python scripts/run_trading.py analyze …</code> written to{" "}
        <code className="text-indigo-300">data/output/trading_runs/…/run_bundle.json</code>. Schema version is stable for UI; use{" "}
        <strong>Compare run</strong> to see deltas vs another bundle.
      </p>

      {err && <div className="mb-4 text-red-400 text-sm">{err}</div>}

      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-[var(--text-dim)]">Primary run</span>
          <div className="relative">
            <select
              className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-3 py-2 appearance-none"
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
            >
              <option value="">Select run_bundle.json…</option>
              {bundleRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.relPath} ({r.modified.slice(0, 10)})
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-3 text-[var(--text-dim)] pointer-events-none" size={16} />
          </div>
        </label>
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-[var(--text-dim)] flex items-center gap-2">
            <GitCompare size={14} /> Compare with (optional)
          </span>
          <select
            className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-3 py-2"
            value={secondary}
            onChange={(e) => setSecondary(e.target.value)}
          >
            <option value="">None</option>
            {bundleRuns.map((r) => (
              <option key={`c-${r.id}`} value={r.id}>
                {r.relPath}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <div className="text-sm text-[var(--text-dim)] mb-4">Loading bundle…</div>}

      {bundle && (
        <>
          <div className="flex flex-wrap gap-4 text-sm mb-4 border border-[var(--border)] rounded-lg p-4 bg-[var(--bg-card)]">
            <span>
              schema: <strong className="text-indigo-300">{bundle.schema_version}</strong>
            </span>
            <span>
              run_id: <strong>{bundle.run_id}</strong>
            </span>
            <span>
              as_of: <strong>{bundle.as_of_date}</strong>
            </span>
            <span>
              fusion: <strong>{bundle.fusion}</strong>
            </span>
            <span>
              rows: <strong>{bundle.row_count}</strong>
            </span>
          </div>

          {comparison && (
            <div className="mb-6 p-4 rounded-lg border border-yellow-500/30 bg-yellow-500/5 text-sm">
              <div className="font-medium text-yellow-200 mb-2">Delta vs comparison run</div>
              <div className="flex flex-wrap gap-4">
                <span>Compared tickers: {comparison.summary.tickers_compared}</span>
                <span className="text-orange-300">Signal/score changes: {comparison.summary.signal_changes}</span>
                <span>Added in B: {comparison.summary.added}</span>
                <span>Removed in B: {comparison.summary.removed}</span>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-4 mb-4 items-center">
            <label className="text-sm flex items-center gap-2">
              Sector filter
              <select
                className="bg-[var(--bg-card)] border border-[var(--border)] rounded px-2 py-1"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              >
                {sectors.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {matrix && (
            <div className="mb-6 grid md:grid-cols-2 gap-4">
              <pre className="text-xs bg-black/40 border border-[var(--border)] rounded-lg p-3 overflow-auto max-h-48">
                {JSON.stringify(matrix, null, 2)}
              </pre>
              <p className="text-xs text-[var(--text-dim)]">
                Signal alignment tables: fusion vs Phoenix direction counts. Traditional TP/FP/TN/FN populate only when rows include{" "}
                <code>evaluation.signal_correct</code> from a labeled backtest merge.
              </p>
            </div>
          )}

          <div className="overflow-x-auto border border-[var(--border)] rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--text-dim)]">
                  <th className="p-2">Ticker</th>
                  <th className="p-2">Sector</th>
                  <th className="p-2">Fusion</th>
                  <th className="p-2 text-center" title="True positive">
                    TP
                  </th>
                  <th className="p-2 text-center" title="False positive">
                    FP
                  </th>
                  <th className="p-2 text-center" title="True negative">
                    TN
                  </th>
                  <th className="p-2 text-center" title="False negative">
                    FN
                  </th>
                  <th className="p-2">Cat</th>
                  <th className="p-2">Score</th>
                  <th className="p-2">Phoenix</th>
                  <th className="p-2">Fund</th>
                  <th className="p-2">Δ vs B</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => {
                  const cmp = comparison?.per_ticker[row.ticker?.toUpperCase?.() ?? row.ticker];
                  const delta =
                    cmp?.status === "both" && cmp.changed ? (
                      <span className="text-orange-300">
                        {cmp.fusion_signal?.from ?? "?"} → {cmp.fusion_signal?.to ?? "?"}
                      </span>
                    ) : cmp?.status === "added_in_b" ? (
                      <span className="text-green-400">new</span>
                    ) : (
                      "—"
                    );
                  const sc = row.evaluation?.signal_correct;
                  const bucket = confusionBucket(row.fusion_final_signal, sc);
                  const m = confusionCells(bucket);
                  return (
                    <tr key={row.ticker} className="border-b border-[var(--border)]/60 hover:bg-white/5">
                      <td className="p-2 font-mono">{row.ticker}</td>
                      <td className="p-2">{row.sector ?? "—"}</td>
                      <td className="p-2">{row.fusion_final_signal ?? row.error ?? "—"}</td>
                      <td className={`p-2 text-center font-mono ${m.TP ? "text-emerald-400 font-bold" : "text-[var(--text-dim)]"}`}>
                        {m.TP || "—"}
                      </td>
                      <td className={`p-2 text-center font-mono ${m.FP ? "text-red-400 font-bold" : "text-[var(--text-dim)]"}`}>
                        {m.FP || "—"}
                      </td>
                      <td className={`p-2 text-center font-mono ${m.TN ? "text-cyan-400 font-bold" : "text-[var(--text-dim)]"}`}>
                        {m.TN || "—"}
                      </td>
                      <td className={`p-2 text-center font-mono ${m.FN ? "text-amber-400 font-bold" : "text-[var(--text-dim)]"}`}>
                        {m.FN || "—"}
                      </td>
                      <td className="p-2 text-xs font-mono text-[var(--text-dim)]">{bucket}</td>
                      <td className="p-2">{row.fusion_orchestrator_score ?? "—"}</td>
                      <td className="p-2">{row.phoenix_signal ?? "—"}</td>
                      <td className="p-2">{row.fund_signal_normalized ?? "—"}</td>
                      <td className="p-2 text-xs">{delta}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
