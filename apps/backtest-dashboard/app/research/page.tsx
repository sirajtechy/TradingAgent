"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Database,
  Microscope,
  RefreshCw,
  Table2,
  Zap,
} from "lucide-react";
import { fmtMoney, fmtNum, SignalPill, tierBadge } from "./analyze/analyzeUi";

type AgentSource = {
  id: string;
  label: string;
  role: string;
  primary: string;
  fallback: string;
  cli: string;
  tier: string;
};

type WatchRow = {
  ticker: string;
  phoenix_signal?: string;
  phoenix_score?: number | null;
  sector?: string;
  entry_price?: number | null;
  stop_price?: number | null;
  target_t1?: number | null;
  target_t2?: number | null;
  analyze_cached?: boolean;
  advisory_verdict?: string | null;
  orchestrator_score?: number | null;
  insider_signal?: string | null;
  insider_sell_value?: number | null;
};

type OverviewDoc = {
  ok: boolean;
  error?: string;
  as_of_date?: string;
  master?: {
    source_path?: string;
    buy_count?: number;
    watch_count?: number;
    total_buy_watch?: number;
    analyzed_count?: number;
    pending_analyze?: number;
  };
  signals_export?: { exists?: boolean; path?: string; buy?: number; watch?: number };
  agents?: AgentSource[];
  watchlist?: WatchRow[];
  pipeline?: Record<string, string>;
};

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
      <div className="text-xs uppercase tracking-wide text-[var(--text-dim)] mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs text-[var(--text-dim)] mt-1">{sub}</div>}
    </div>
  );
}

export default function ResearchOverviewPage() {
  const [doc, setDoc] = useState<OverviewDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tradeFocus, setTradeFocus] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setErr(null);
    const q = tradeFocus ? "?trade_focus=1" : "";
    fetch(`/api/research/overview${q}`)
      .then(async (r) => {
        const d = (await r.json()) as OverviewDoc;
        if (!d.ok) throw new Error(d.error || "Failed to load overview");
        setDoc(d);
      })
      .catch((e) => {
        setDoc(null);
        setErr(e instanceof Error ? e.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, [tradeFocus]);

  useEffect(() => {
    load();
  }, [load]);

  const m = doc?.master;
  const wl = doc?.watchlist ?? [];

  return (
    <div className="p-6 md:p-8 max-w-[1600px] mx-auto space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Research Lab Overview</h1>
          <p className="text-sm text-[var(--text-dim)] mt-1 max-w-2xl">
            Live pipeline from <code className="text-emerald-400/90">./bin/mts daily</code> → Phoenix
            pilot → deep analyze before you trade. Legacy CWAF dashboard archived.
          </p>
          {doc?.as_of_date && (
            <p className="text-xs text-[var(--text-dim)] mt-2">
              Signal date: <strong className="text-[var(--text)]">{doc.as_of_date}</strong>
              {m?.source_path && (
                <>
                  {" "}
                  · <code className="text-emerald-400/80">{m.source_path}</code>
                </>
              )}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-[var(--border)] hover:bg-[var(--bg-card)]"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <Link
            href="/research/console"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-200"
          >
            <Zap size={14} />
            Command Center
          </Link>
          <Link
            href="/research/phoenix"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-indigo-500/20 border border-indigo-500/40 text-indigo-200"
          >
            <Table2 size={14} />
            Phoenix pilot
          </Link>
          <Link
            href="/research/backtests"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-teal-500/20 border border-teal-500/40 text-teal-200"
          >
            <Database size={14} />
            Backtest registry
          </Link>
          <Link
            href="/research/analyze/watchlist"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-200"
          >
            <Microscope size={14} />
            BUY/WATCH dive
          </Link>
        </div>
      </header>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm flex gap-2">
          <AlertTriangle size={16} className="shrink-0 mt-0.5 text-amber-400" />
          <div>
            <p>{err}</p>
            <p className="text-[var(--text-dim)] mt-1">
              Run: <code>./bin/mts daily</code> then refresh.
            </p>
          </div>
        </div>
      )}

      {m && (
        <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Stat label="BUY" value={m.buy_count ?? 0} />
          <Stat label="WATCH" value={m.watch_count ?? 0} />
          <Stat
            label="Deep analyzed"
            value={m.analyzed_count ?? 0}
            sub={`${m.pending_analyze ?? 0} pending`}
          />
          <Stat
            label="Export signals"
            value={doc?.signals_export?.exists ? "Ready" : "Missing"}
            sub={doc?.signals_export?.exists ? "Run export to refresh" : "./bin/mts export"}
          />
          <Stat label="Total BUY+WATCH" value={m.total_buy_watch ?? 0} />
          <Stat label="Signal date" value={doc?.as_of_date ?? "—"} />
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--text-dim)] flex items-center gap-2">
            <Database size={14} />
            Agent data sources (full fusion)
          </h2>
        </div>
        <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-card)] text-xs uppercase text-[var(--text-dim)]">
              <tr>
                <th className="text-left px-3 py-2">Agent</th>
                <th className="text-left px-3 py-2">Role</th>
                <th className="text-left px-3 py-2">Primary API</th>
                <th className="text-left px-3 py-2">Fallback</th>
                <th className="text-left px-3 py-2">CLI</th>
              </tr>
            </thead>
            <tbody>
              {(doc?.agents ?? []).map((a) => {
                const badge = tierBadge(a.tier);
                return (
                  <tr key={a.id} className="border-t border-[var(--border)]">
                    <td className="px-3 py-2">
                      <div className="font-medium">{a.label}</div>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[var(--text-dim)] max-w-xs">{a.role}</td>
                    <td className="px-3 py-2">{a.primary}</td>
                    <td className="px-3 py-2 text-[var(--text-dim)]">{a.fallback}</td>
                    <td className="px-3 py-2">
                      <code className="text-[10px] text-emerald-400/90">{a.cli}</code>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--text-dim)]">
            Pre-trade checklist — Phoenix levels + deep analyze
          </h2>
          <label className="flex items-center gap-2 text-xs text-[var(--text-dim)]">
            <input
              type="checkbox"
              checked={tradeFocus}
              onChange={(e) => setTradeFocus(e.target.checked)}
            />
            Trade focus (BUY + WATCH score &gt; 60)
          </label>
        </div>
        <p className="text-xs text-[var(--text-dim)] mb-3">
          Entry/stop/targets from today&apos;s <code>master_pilot.json</code>. Run{" "}
          <code>./bin/mts analyze --watchlist --fusion full --refresh-context</code> to fill deep
          analyze columns (8 agents + SEC insider).
        </p>
        <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--bg-card)] text-xs uppercase text-[var(--text-dim)]">
              <tr>
                <th className="text-left px-3 py-2">Ticker</th>
                <th className="text-left px-3 py-2">Phoenix</th>
                <th className="text-right px-3 py-2">Entry</th>
                <th className="text-right px-3 py-2">Stop</th>
                <th className="text-right px-3 py-2">T1</th>
                <th className="text-right px-3 py-2">T2</th>
                <th className="text-left px-3 py-2">Deep analyze</th>
                <th className="text-left px-3 py-2">Advisory</th>
                <th className="text-right px-3 py-2">Orch</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {wl.length === 0 && !loading && (
                <tr>
                  <td colSpan={10} className="px-3 py-8 text-center text-[var(--text-dim)]">
                    No BUY/WATCH rows. Run ./bin/mts daily.
                  </td>
                </tr>
              )}
              {wl.map((row) => (
                <tr key={row.ticker} className="border-t border-[var(--border)] hover:bg-[var(--bg)]/30">
                  <td className="px-3 py-2 font-medium">{row.ticker}</td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <SignalPill signal={row.phoenix_signal} />
                      <span className="text-xs text-[var(--text-dim)]">
                        {fmtNum(row.phoenix_score, 0)}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtMoney(row.entry_price, 2)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtMoney(row.stop_price, 2)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtMoney(row.target_t1, 2)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtMoney(row.target_t2, 2)}</td>
                  <td className="px-3 py-2">
                    {row.analyze_cached ? (
                      <span className="text-emerald-400 text-xs">Cached</span>
                    ) : (
                      <span className="text-amber-400 text-xs">Pending</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <SignalPill signal={row.advisory_verdict} />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {fmtNum(row.orchestrator_score, 0)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      href={`/research/analyze?ticker=${encodeURIComponent(row.ticker)}`}
                      className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      Analyze <ArrowRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {doc?.pipeline && (
        <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
            Daily commands
          </h2>
          <div className="grid gap-2 sm:grid-cols-2 text-xs font-mono">
            {Object.entries(doc.pipeline).map(([k, v]) => (
              <div key={k} className="flex gap-2">
                <span className="text-[var(--text-dim)] shrink-0 w-28">{k.replace(/_/g, " ")}</span>
                <code className="text-emerald-400/90 break-all">{v}</code>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
