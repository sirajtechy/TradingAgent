"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Download, RefreshCw } from "lucide-react";

type SignalRow = {
  signal_date: string;
  ticker: string;
  phoenix_signal?: string;
  sector?: string;
  source_json?: string;
  phoenix_score?: number;
  fusion_final_signal?: string;
  fusion_orchestrator_score?: number;
  entry_price?: number;
  pattern_name?: string;
};

type ApiDoc = {
  ok: boolean;
  error?: string;
  expectedPath?: string;
  summary?: {
    date_from?: string;
    date_to?: string;
    buy?: number;
    watch?: number;
    signals_deduped?: number;
    sources_scanned?: number;
    signal_dates?: string[];
  };
  signals?: SignalRow[];
  xlsxPath?: string;
  xlsxExists?: boolean;
  generated_at?: string;
};

export default function ResearchSignalsPage() {
  const [doc, setDoc] = useState<ApiDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<"ALL" | "BUY" | "WATCH">("ALL");
  const [sector, setSector] = useState("All");
  const [date, setDate] = useState("All");

  const load = useCallback(() => {
    setLoading(true);
    setErr(null);
    fetch("/api/research/signals")
      .then(async (r) => {
        const d = (await r.json()) as ApiDoc;
        if (!r.ok || !d.ok) {
          throw new Error(d.error || "Failed to load");
        }
        setDoc(d);
      })
      .catch((e) => {
        setDoc(null);
        setErr(e instanceof Error ? e.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rows = doc?.signals ?? [];

  const sectors = useMemo(() => {
    const s = new Set<string>();
    rows.forEach((r) => {
      if (r.sector) s.add(String(r.sector));
    });
    return ["All", ...Array.from(s).sort()];
  }, [rows]);

  const dates = useMemo(() => {
    const s = new Set<string>();
    rows.forEach((r) => {
      if (r.signal_date) s.add(r.signal_date);
    });
    return ["All", ...Array.from(s).sort().reverse()];
  }, [rows]);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (filter !== "ALL" && String(r.phoenix_signal).toUpperCase() !== filter) return false;
      if (sector !== "All" && r.sector !== sector) return false;
      if (date !== "All" && r.signal_date !== date) return false;
      return true;
    });
  }, [rows, filter, sector, date]);

  const summary = doc?.summary;

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-4 md:px-8">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center gap-4 justify-between">
          <div>
            <Link
              href="/research"
              className="text-sm text-[var(--text-dim)] hover:text-[var(--text)] inline-flex items-center gap-1 mb-2"
            >
              <ArrowLeft size={14} /> Research Lab
            </Link>
            <h1 className="text-xl font-semibold">Reconciled signals</h1>
            <p className="text-sm text-[var(--text-dim)] mt-1">
              BUY & WATCH deduped across unified and sector pilots
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-[var(--border)] hover:bg-white/5"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
        {loading && <p className="text-[var(--text-dim)]">Loading…</p>}

        {err && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
            <p className="font-medium text-amber-200">No signal dump yet</p>
            <p className="mt-2 text-[var(--text-dim)]">{err}</p>
            <pre className="mt-3 text-xs bg-black/30 p-3 rounded overflow-x-auto">
              ./bin/mts export --from 2026-05-10 --to 2026-05-28 --signals BUY,WATCH
            </pre>
          </div>
        )}

        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "BUY", value: summary.buy ?? 0 },
              { label: "WATCH", value: summary.watch ?? 0 },
              { label: "Sources", value: summary.sources_scanned ?? 0 },
              { label: "Deduped rows", value: summary.signals_deduped ?? 0 },
            ].map((c) => (
              <div
                key={c.label}
                className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4"
              >
                <div className="text-xs text-[var(--text-dim)] uppercase tracking-wide">{c.label}</div>
                <div className="text-2xl font-semibold mt-1">{c.value}</div>
              </div>
            ))}
          </div>
        )}

        {summary && (
          <p className="text-sm text-[var(--text-dim)]">
            Range {summary.date_from} → {summary.date_to}
            {doc?.generated_at && (
              <> · generated {new Date(doc.generated_at).toLocaleString()}</>
            )}
            {doc?.xlsxExists && doc?.xlsxPath && (
              <> · Excel at <code className="text-emerald-400/90">{doc.xlsxPath}</code></>
            )}
          </p>
        )}

        {!loading && !err && (
          <>
            <div className="flex flex-wrap gap-3 items-center">
              <div className="flex rounded-lg border border-[var(--border)] overflow-hidden text-sm">
                {(["ALL", "BUY", "WATCH"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setFilter(f)}
                    className={`px-3 py-1.5 ${
                      filter === f ? "bg-emerald-500/20 text-emerald-300" : "hover:bg-white/5"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <select
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="text-sm bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2 py-1.5"
              >
                {dates.map((d) => (
                  <option key={d} value={d}>
                    {d === "All" ? "All dates" : d}
                  </option>
                ))}
              </select>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="text-sm bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2 py-1.5"
              >
                {sectors.map((s) => (
                  <option key={s} value={s}>
                    {s === "All" ? "All sectors" : s}
                  </option>
                ))}
              </select>
              <span className="text-sm text-[var(--text-dim)]">{filtered.length} rows</span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--bg-card)] text-left text-[var(--text-dim)]">
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Ticker</th>
                    <th className="px-3 py-2">Phoenix</th>
                    <th className="px-3 py-2">Sector</th>
                    <th className="px-3 py-2">Fusion</th>
                    <th className="px-3 py-2 text-right">Px score</th>
                    <th className="px-3 py-2 text-right">Entry</th>
                    <th className="px-3 py-2">Pattern</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => (
                    <tr
                      key={`${r.signal_date}-${r.ticker}-${r.source_json}`}
                      className="border-b border-[var(--border)]/50 hover:bg-white/[0.02]"
                    >
                      <td className="px-3 py-2 whitespace-nowrap">{r.signal_date}</td>
                      <td className="px-3 py-2 font-medium">{r.ticker}</td>
                      <td className="px-3 py-2">
                        <span
                          className={
                            String(r.phoenix_signal).toUpperCase() === "BUY"
                              ? "text-emerald-400"
                              : "text-amber-300"
                          }
                        >
                          {r.phoenix_signal}
                        </span>
                      </td>
                      <td className="px-3 py-2">{r.sector ?? "—"}</td>
                      <td className="px-3 py-2">{r.fusion_final_signal ?? "—"}</td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {r.phoenix_score != null ? Number(r.phoenix_score).toFixed(1) : "—"}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {r.entry_price != null ? Number(r.entry_price).toFixed(2) : "—"}
                      </td>
                      <td className="px-3 py-2 text-[var(--text-dim)]">{r.pattern_name ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && (
                <p className="p-6 text-center text-[var(--text-dim)]">No rows match filters.</p>
              )}
            </div>

            <p className="text-xs text-[var(--text-dim)] flex items-center gap-1">
              <Download size={12} />
              Full export: run <code>./bin/mts export</code> for Excel with Sources & Reconciliation sheets.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
