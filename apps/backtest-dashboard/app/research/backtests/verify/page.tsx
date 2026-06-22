"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, AlertTriangle, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import type { VerifiedSummaryDoc, VerifiedTickerRow, VerifyIndexDoc, VerifyIndexRun } from "@/app/lib/backtestVerify";

type VerifyPayload = {
  ok?: boolean;
  error?: string;
  artifact?: { rel?: string; exists?: boolean } | null;
  report?: {
    exists?: boolean;
    rel?: string;
    summary?: Record<string, unknown>;
    verified_summary?: VerifiedSummaryDoc;
    meta?: Record<string, unknown>;
  } | null;
  index?: VerifyIndexDoc;
};

function StatCard({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string | number;
  sub?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const tones = {
    default: "border-[var(--border)]",
    good: "border-emerald-500/40 bg-emerald-500/5",
    warn: "border-amber-500/40 bg-amber-500/5",
    bad: "border-red-500/40 bg-red-500/5",
  };
  return (
    <div className={`rounded-lg border p-3 ${tones[tone]}`}>
      <div className="text-[10px] uppercase tracking-wide text-[var(--text-dim)]">{label}</div>
      <div className="text-xl font-semibold mt-0.5">{value}</div>
      {sub ? <div className="text-[10px] text-[var(--text-dim)] mt-1">{sub}</div> : null}
    </div>
  );
}

function StatusBadge({ run }: { run: VerifyIndexRun }) {
  if (!run.verified) {
    return (
      <span className="inline-flex items-center gap-1 text-amber-300 text-[10px]">
        <AlertTriangle size={12} /> pending
      </span>
    );
  }
  if ((run.disputed_tp ?? 0) > 0 || (run.rows_fail ?? 0) > 0) {
    return (
      <span className="inline-flex items-center gap-1 text-orange-300 text-[10px]">
        <AlertTriangle size={12} /> review
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-emerald-300 text-[10px]">
      <CheckCircle2 size={12} /> ok
    </span>
  );
}

function TickerTable({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: VerifiedTickerRow[];
  tone: "good" | "warn" | "bad";
}) {
  if (!rows.length) return null;
  const header =
    tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-red-300";
  return (
    <section className="space-y-2">
      <h2 className={`text-sm font-semibold ${header}`}>
        {title} ({rows.length})
      </h2>
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full text-xs">
          <thead className="bg-[var(--bg-card)] text-[var(--text-dim)]">
            <tr>
              <th className="text-left p-2">Ticker</th>
              <th className="text-left p-2">Entry</th>
              <th className="text-left p-2">Target</th>
              <th className="text-left p-2">Hit date</th>
              <th className="text-left p-2">Artifact hit</th>
              <th className="text-left p-2">Polygon hit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.ticker} className="border-t border-[var(--border)]">
                <td className="p-2 font-medium">{r.ticker}</td>
                <td className="p-2">{r.entry_price ?? "—"}</td>
                <td className="p-2">{r.target_price ?? "—"}</td>
                <td className="p-2">{r.target_hit_date ?? "—"}</td>
                <td className="p-2">{r.artifact_target_hit == null ? "—" : r.artifact_target_hit ? "yes" : "no"}</td>
                <td className="p-2">
                  {r.recomputed_target_hit == null ? "—" : r.recomputed_target_hit ? "yes" : "no"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VerifyPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const signalFromUrl = searchParams.get("signal_date") ?? "";
  const runFromUrl = searchParams.get("run") ?? "";
  const relFromUrl = searchParams.get("rel") ?? "";

  const [data, setData] = useState<VerifyPayload | null>(null);
  const [index, setIndex] = useState<VerifyIndexDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [batchRunning, setBatchRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const query = useMemo(() => {
    if (signalFromUrl) return `signal_date=${encodeURIComponent(signalFromUrl)}`;
    if (runFromUrl) return `run=${encodeURIComponent(runFromUrl)}`;
    if (relFromUrl) return `rel=${encodeURIComponent(relFromUrl)}`;
    return "latest=1";
  }, [signalFromUrl, runFromUrl, relFromUrl]);

  const loadIndex = useCallback(async () => {
    const r = await fetch("/api/research/backtests/verify?index=1");
    const d = await r.json();
    if (d.index) setIndex(d.index as VerifyIndexDoc);
    return d.index as VerifyIndexDoc;
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [detailRes] = await Promise.all([
        fetch(`/api/research/backtests/verify?${query}`),
        loadIndex(),
      ]);
      const d = (await detailRes.json()) as VerifyPayload;
      if (!d.ok && d.error) throw new Error(d.error);
      setData(d);
      if (d.index) setIndex(d.index);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [query, loadIndex]);

  const selectSignalDate = (sd: string) => {
    router.push(`/research/backtests/verify?signal_date=${encodeURIComponent(sd)}`);
  };

  const runVerify = useCallback(async () => {
    setRunning(true);
    setErr(null);
    try {
      const body: Record<string, unknown> = { rateLimit: 2 };
      if (signalFromUrl) {
        body.rel = `sector_information-technology_${signalFromUrl}/master_pilot.json`;
      } else if (runFromUrl) body.run = runFromUrl;
      else if (relFromUrl) body.rel = relFromUrl;
      const r = await fetch("/api/research/backtests/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!d.ok && d.error) throw new Error(d.error);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Verify run failed");
    } finally {
      setRunning(false);
    }
  }, [load, signalFromUrl, runFromUrl, relFromUrl]);

  const runBatch = useCallback(async () => {
    setBatchRunning(true);
    setErr(null);
    try {
      const r = await fetch("/api/research/backtests/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch: true, rateLimit: 2, glob: "sector_information-technology_*" }),
      });
      const d = await r.json();
      if (!d.ok && d.error) throw new Error(d.error);
      if (d.index) setIndex(d.index);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Batch verify failed (may still be running server-side)");
    } finally {
      setBatchRunning(false);
    }
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  const runs = index?.runs ?? [];
  const agg = index?.aggregate;
  const selectedSignal =
    signalFromUrl ||
    (data?.artifact?.rel?.match(/_(\d{4}-\d{2}-\d{2})\/master_pilot/)?.[1] ?? "") ||
    runs.find((r) => r.verified)?.signal_date ||
    "";

  const selectedIndexRun = runs.find((r) => r.signal_date === selectedSignal);
  const vs = data?.report?.verified_summary;
  const claimed = vs?.artifact_claimed;
  const verified = vs?.polygon_verified;
  const hasReport = Boolean(data?.report?.exists);

  return (
    <div className="p-5 max-w-6xl mx-auto space-y-5">
      <header className="flex flex-wrap items-start gap-3">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-cyan-400" size={20} />
            <h1 className="text-lg font-semibold text-cyan-300">Polygon verification</h1>
          </div>
          <p className="text-xs text-[var(--text-dim)] mt-0.5 max-w-2xl">
            Cross-check every IT sector backtest date against independent Polygon bars. Confirms
            bullish true positives (target hit) match what the backtest reported.
          </p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border)] hover:bg-[var(--bg-card)] disabled:opacity-50"
          >
            <RefreshCw size={14} className={`inline mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => runBatch()}
            disabled={batchRunning}
            className="px-3 py-1.5 text-xs rounded-lg bg-cyan-700/30 border border-cyan-500/50 text-cyan-100 hover:bg-cyan-700/40 disabled:opacity-50"
          >
            {batchRunning ? "Batch running…" : "Verify all IT runs"}
          </button>
        </div>
      </header>

      <div className="text-xs text-[var(--text-dim)] flex flex-wrap gap-3">
        <Link href="/research/backtests" className="text-emerald-400 hover:underline">
          ← Technical backtest
        </Link>
        {index?.updated_at ? <span>Index updated {index.updated_at.slice(0, 19)}</span> : null}
      </div>

      {err ? (
        <div className="text-sm text-red-300 border border-red-500/30 rounded-lg p-3">{err}</div>
      ) : null}

      {agg ? (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <StatCard label="Backtest dates" value={agg.total_artifacts ?? 0} sub={`${agg.verified_count ?? 0} verified`} />
          <StatCard
            label="Total artifact TP"
            value={agg.total_artifact_tp ?? 0}
            sub="bullish winners claimed"
          />
          <StatCard
            label="Polygon confirmed TP"
            value={agg.total_confirmed_tp ?? 0}
            sub={
              agg.overall_tp_confirmation_rate_pct != null
                ? `${agg.overall_tp_confirmation_rate_pct}% overall`
                : undefined
            }
            tone="good"
          />
          <StatCard
            label="Disputed TP"
            value={agg.total_disputed_tp ?? 0}
            tone={(agg.total_disputed_tp ?? 0) > 0 ? "bad" : "default"}
          />
          <StatCard
            label="Missing verify"
            value={agg.missing_count ?? 0}
            tone={(agg.missing_count ?? 0) > 0 ? "warn" : "default"}
          />
        </div>
      ) : null}

      {/* Timeline — all signal dates */}
      <section className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-sm font-semibold text-cyan-200">All backtest dates</h2>
          <select
            className="text-xs bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 min-w-[200px]"
            value={selectedSignal}
            onChange={(e) => selectSignalDate(e.target.value)}
          >
            {runs.length === 0 ? <option value="">No runs indexed</option> : null}
            {runs.map((r) => (
              <option key={r.signal_date} value={r.signal_date ?? ""}>
                {r.signal_date} · {r.ticker_count ?? "?"}tk · TP {r.confirmed_tp ?? "?"}/{r.artifact_tp ?? "?"}{" "}
                {r.verified ? "" : "(pending)"}
              </option>
            ))}
          </select>
        </div>
        <div className="overflow-x-auto rounded-lg border border-[var(--border)] max-h-64 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="bg-[var(--bg-card)] text-[var(--text-dim)] sticky top-0">
              <tr>
                <th className="text-left p-2">Signal date</th>
                <th className="text-left p-2">Tickers</th>
                <th className="text-left p-2">Pass rate</th>
                <th className="text-left p-2">Artifact TP</th>
                <th className="text-left p-2">Confirmed TP</th>
                <th className="text-left p-2">Disputed</th>
                <th className="text-left p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr
                  key={r.signal_date}
                  className={`border-t border-[var(--border)] cursor-pointer hover:bg-white/5 ${
                    r.signal_date === selectedSignal ? "bg-cyan-500/10" : ""
                  }`}
                  onClick={() => r.signal_date && selectSignalDate(r.signal_date)}
                >
                  <td className="p-2 font-medium text-cyan-200">{r.signal_date}</td>
                  <td className="p-2">{r.ticker_count ?? "—"}</td>
                  <td className="p-2">
                    {r.pass_rate_pct != null ? `${r.pass_rate_pct}%` : r.verified ? "—" : "—"}
                  </td>
                  <td className="p-2">{r.artifact_tp ?? "—"}</td>
                  <td className="p-2 text-emerald-300">{r.confirmed_tp ?? "—"}</td>
                  <td className="p-2 text-orange-300">{r.disputed_tp ?? "—"}</td>
                  <td className="p-2">
                    <StatusBadge run={r} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Selected date detail */}
      <section className="border border-[var(--border)] rounded-lg p-4 space-y-4 bg-[var(--bg-card)]/50">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-sm font-semibold">
            Detail: <span className="text-cyan-300">{selectedSignal || "—"}</span>
          </h2>
          <button
            type="button"
            onClick={() => runVerify()}
            disabled={running || !selectedSignal}
            className="text-xs px-2.5 py-1 rounded border border-cyan-500/40 text-cyan-200 hover:bg-cyan-500/10 disabled:opacity-50"
          >
            {running ? "Verifying…" : hasReport ? "Re-run this date" : "Verify this date"}
          </button>
          {selectedIndexRun && !selectedIndexRun.verified ? (
            <span className="text-xs text-amber-300 flex items-center gap-1">
              <XCircle size={12} /> Not verified yet
            </span>
          ) : null}
        </div>

        {!hasReport && !loading ? (
          <p className="text-xs text-[var(--text-dim)]">
            No Polygon report for this date. Click <strong>Verify this date</strong> or run{" "}
            <strong>Verify all IT runs</strong>.
          </p>
        ) : null}

        {hasReport && vs ? (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Artifact bullish TP" value={claimed?.bullish_tp ?? 0} />
              <StatCard
                label="Polygon confirmed TP"
                value={verified?.confirmed_tp ?? 0}
                sub={
                  verified?.tp_confirmation_rate_pct != null
                    ? `${verified.tp_confirmation_rate_pct}%`
                    : undefined
                }
                tone="good"
              />
              <StatCard
                label="Disputed TP"
                value={verified?.disputed_tp ?? 0}
                tone={(verified?.disputed_tp ?? 0) > 0 ? "bad" : "default"}
              />
              <StatCard
                label="Price rows pass"
                value={verified?.price_rows_pass ?? 0}
                sub={`${verified?.price_rows_fail ?? 0} fail · ${verified?.price_rows_skip ?? 0} skip`}
              />
            </div>

            {(verified?.confirmed_tp ?? 0) > 0 && (verified?.disputed_tp ?? 0) === 0 ? (
              <div className="flex items-center gap-2 text-sm text-emerald-300 border border-emerald-500/30 rounded-lg p-3 bg-emerald-500/5">
                <CheckCircle2 size={16} />
                All claimed bullish true positives confirmed by Polygon for this date.
              </div>
            ) : null}

            <TickerTable title="Verified true positives" rows={vs.verified_tp_tickers ?? []} tone="good" />
            <TickerTable title="Disputed true positives" rows={vs.disputed_tp_tickers ?? []} tone="bad" />
            <TickerTable title="Verified false positives" rows={vs.verified_fp_tickers ?? []} tone="warn" />
          </>
        ) : null}
      </section>
    </div>
  );
}

export default function BacktestVerifyPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-[var(--text-dim)]">Loading verification…</div>}>
      <VerifyPanel />
    </Suspense>
  );
}
