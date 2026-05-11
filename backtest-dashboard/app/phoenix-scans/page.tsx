"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  X,
  TrendingUp,
  Minus,
  TrendingDown,
} from "lucide-react";

type PhoenixSignal = "BUY" | "WATCH" | "AVOID";

type RunListItem = {
  date: string;
  hasFile?: boolean;
  sectors?: string[];
  tickers?: number | null;
  elapsed_sec?: number | null;
  generated_at?: string | null;
};

type RunMeta = {
  as_of_date?: string;
  sectors?: string[];
  tickers_requested?: number;
  results?: number;
  errors?: number;
  workers?: number;
  elapsed_sec?: number;
  generated_at?: string;
};

type ResultRow = {
  ticker: string;
  sector: string;
  as_of_date: string;
  signal: PhoenixSignal;
  score: number;
  hard_filter_passed: boolean;
  hard_filter_reason?: string | null;
  stage?: { stage?: number; label?: string; action?: string } | null;
  pattern?: {
    pattern_name?: string;
    confirmed?: boolean;
    volume_confirmed?: boolean;
    pivot_price?: number;
    confidence?: number;
  } | null;
  entry?: { entry_type?: string; entry_price?: number; trigger_description?: string } | null;
  risk?: { stop_price?: number; target_1?: number; target_2?: number; reward_risk?: number } | null;
  warnings?: string[];
};

type RunPayload = { meta: RunMeta; results: ResultRow[]; errors: any[] };

type TickerDetail = ResultRow & { report?: string };

function badgeClass(signal: PhoenixSignal) {
  if (signal === "BUY") return "bg-green-500/15 text-green-400 border-green-500/30";
  if (signal === "WATCH") return "bg-yellow-500/15 text-yellow-300 border-yellow-500/30";
  return "bg-red-500/15 text-red-400 border-red-500/30";
}

function SignalIcon({ s }: { s: PhoenixSignal }) {
  if (s === "BUY") return <TrendingUp size={14} className="text-green-400" />;
  if (s === "WATCH") return <Minus size={14} className="text-yellow-300" />;
  return <TrendingDown size={14} className="text-red-400" />;
}

function fmt(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return typeof n === "number" ? n.toFixed(1) : String(n);
}

function fmtPct(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function calcExtensionPct(row: ResultRow): number | null {
  const pivot = row.pattern?.pivot_price;
  const entry = row.entry?.entry_price;
  if (typeof pivot !== "number" || typeof entry !== "number" || pivot <= 0) return null;
  return ((entry - pivot) / pivot) * 100;
}

export default function PhoenixScansPage() {
  const [mounted, setMounted] = useState(false);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [data, setData] = useState<RunPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("All");
  const [signalFilter, setSignalFilter] = useState<"All" | PhoenixSignal>("All");
  const [onlyPassed, setOnlyPassed] = useState(false);
  const [sortBy, setSortBy] = useState<"score" | "ticker">("score");

  const [openDetail, setOpenDetail] = useState<TickerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [compareMode, setCompareMode] = useState(false);
  const [compareDate, setCompareDate] = useState<string>("");
  const [compareData, setCompareData] = useState<RunPayload | null>(null);
  const [extensionThresholdPct, setExtensionThresholdPct] = useState<number>(6);

  const closeDetail = () => {
    setDetailLoading(false);
    setOpenDetail(null);
  };

  const refreshRuns = async () => {
    setErr(null);
    try {
      const r = await fetch("/api/phoenix-scans", { cache: "no-store" });
      const j = await r.json();
      const list: RunListItem[] = j?.runs ?? [];
      setRuns(list);
      if (!selectedDate && list.length > 0) setSelectedDate(list[0].date);
    } catch {
      setErr("Failed to load runs list");
    }
  };

  const loadRun = async (date: string) => {
    if (!date) return;
    setLoading(true);
    setErr(null);
    setData(null);
    try {
      const r = await fetch(`/api/phoenix-scans/${encodeURIComponent(date)}`, { cache: "no-store" });
      const j = await r.json();
      if (j?.error) throw new Error(j.error);
      setData(j);
    } catch (e: any) {
      setErr(e?.message || "Failed to load run");
    } finally {
      setLoading(false);
    }
  };

  const loadRunRaw = async (date: string): Promise<RunPayload> => {
    const r = await fetch(`/api/phoenix-scans/${encodeURIComponent(date)}`, { cache: "no-store" });
    const j = await r.json();
    if (j?.error) throw new Error(j.error);
    return j as RunPayload;
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    refreshRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close detail drawer via Escape
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDetail();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedDate) return;
    if (compareMode) return; // compare mode loads both dates separately
    loadRun(selectedDate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, compareMode]);

  useEffect(() => {
    if (!compareMode) {
      setCompareData(null);
      return;
    }
    if (!selectedDate || !compareDate) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const [base, comp] = await Promise.all([loadRunRaw(selectedDate), loadRunRaw(compareDate)]);
        if (cancelled) return;
        setData(base);
        setCompareData(comp);
      } catch (e: any) {
        if (cancelled) return;
        setErr(e?.message || "Failed to load compare runs");
        setCompareData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareMode, selectedDate, compareDate]);

  const sectors = useMemo(() => {
    const s = new Set<string>();
    for (const r of data?.results ?? []) s.add(r.sector);
    return ["All", ...Array.from(s).sort()];
  }, [data]);

  type CompareStatus = "New" | "Dropped" | "Overlap";
  type CompareRow = {
    key: string;
    ticker: string;
    sector: string;
    status: CompareStatus;
    base?: ResultRow | null;
    comp?: ResultRow | null;
    baseExtPct: number | null;
    compExtPct: number | null;
    baseExtended: boolean;
    compExtended: boolean;
  };

  const compareRows = useMemo(() => {
    if (!compareMode) return [] as CompareRow[];
    const base = data?.results ?? [];
    const comp = compareData?.results ?? [];
    const baseMap = new Map<string, ResultRow>();
    const compMap = new Map<string, ResultRow>();

    // If a ticker appears in multiple sectors (rare), prefer the row with higher score.
    for (const r of base) {
      const prev = baseMap.get(r.ticker);
      if (!prev || (r.score ?? 0) > (prev.score ?? 0)) baseMap.set(r.ticker, r);
    }
    for (const r of comp) {
      const prev = compMap.get(r.ticker);
      if (!prev || (r.score ?? 0) > (prev.score ?? 0)) compMap.set(r.ticker, r);
    }

    const tickers = new Set<string>([...baseMap.keys(), ...compMap.keys()]);
    const rows: CompareRow[] = [];
    for (const t of tickers) {
      const b = baseMap.get(t) ?? null;
      const c = compMap.get(t) ?? null;
      const status: CompareStatus = b && c ? "Overlap" : c ? "New" : "Dropped";
      const sector = (c?.sector || b?.sector || "—") as string;
      const baseExtPct = b ? calcExtensionPct(b) : null;
      const compExtPct = c ? calcExtensionPct(c) : null;
      const baseExtended = baseExtPct != null && baseExtPct > extensionThresholdPct;
      const compExtended = compExtPct != null && compExtPct > extensionThresholdPct;
      rows.push({
        key: t,
        ticker: t,
        sector,
        status,
        base: b,
        comp: c,
        baseExtPct,
        compExtPct,
        baseExtended,
        compExtended,
      });
    }

    const q = search.trim().toLowerCase();
    const filteredRows = rows.filter((r) => {
      const matchSearch =
        q === "" ||
        r.ticker.toLowerCase().includes(q) ||
        (r.base?.pattern?.pattern_name || "").toLowerCase().includes(q) ||
        (r.comp?.pattern?.pattern_name || "").toLowerCase().includes(q) ||
        (r.base?.stage?.label || "").toLowerCase().includes(q) ||
        (r.comp?.stage?.label || "").toLowerCase().includes(q);
      const matchSector = sectorFilter === "All" || r.sector === sectorFilter;
      const s = (r.comp?.signal || r.base?.signal) as PhoenixSignal | undefined;
      const matchSignal = signalFilter === "All" || s === signalFilter;
      const passed = Boolean(r.comp?.hard_filter_passed ?? r.base?.hard_filter_passed);
      const matchPass = !onlyPassed || passed;
      return matchSearch && matchSector && matchSignal && matchPass;
    });

    filteredRows.sort((a, b) => {
      if (sortBy === "ticker") return a.ticker.localeCompare(b.ticker);
      const sa = a.comp?.score ?? a.base?.score ?? 0;
      const sb = b.comp?.score ?? b.base?.score ?? 0;
      return sb - sa;
    });

    return filteredRows;
  }, [
    compareMode,
    data,
    compareData,
    search,
    sectorFilter,
    signalFilter,
    onlyPassed,
    sortBy,
    extensionThresholdPct,
  ]);

  const filtered = useMemo(() => {
    const rows = data?.results ?? [];
    const q = search.trim().toLowerCase();
    return rows
      .filter((r) => {
        const matchSearch =
          q === "" ||
          r.ticker.toLowerCase().includes(q) ||
          (r.pattern?.pattern_name || "").toLowerCase().includes(q) ||
          (r.stage?.label || "").toLowerCase().includes(q);
        const matchSector = sectorFilter === "All" || r.sector === sectorFilter;
        const matchSignal = signalFilter === "All" || r.signal === signalFilter;
        const matchPass = !onlyPassed || r.hard_filter_passed;
        return matchSearch && matchSector && matchSignal && matchPass;
      })
      .sort((a, b) => {
        if (sortBy === "ticker") return a.ticker.localeCompare(b.ticker);
        return (b.score ?? 0) - (a.score ?? 0);
      });
  }, [data, search, sectorFilter, signalFilter, onlyPassed, sortBy]);

  const stats = useMemo(() => {
    if (compareMode) {
      const rows = compareRows;
      const buy = rows.filter((r) => (r.comp?.signal || r.base?.signal) === "BUY").length;
      const watch = rows.filter((r) => (r.comp?.signal || r.base?.signal) === "WATCH").length;
      const avoid = rows.filter((r) => (r.comp?.signal || r.base?.signal) === "AVOID").length;
      const pass = rows.filter((r) => Boolean(r.comp?.hard_filter_passed ?? r.base?.hard_filter_passed)).length;
      return { buy, watch, avoid, pass, total: rows.length };
    }
    const rows = data?.results ?? [];
    const buy = rows.filter((r) => r.signal === "BUY").length;
    const watch = rows.filter((r) => r.signal === "WATCH").length;
    const avoid = rows.filter((r) => r.signal === "AVOID").length;
    const pass = rows.filter((r) => r.hard_filter_passed).length;
    return { buy, watch, avoid, pass, total: rows.length };
  }, [data]);

  const openTicker = async (row: ResultRow) => {
    if (!selectedDate) return;
    setOpenDetail(null);
    setDetailLoading(true);
    try {
      const url = `/api/phoenix-scans/${encodeURIComponent(selectedDate)}/ticker?ticker=${encodeURIComponent(
        row.ticker
      )}&sector=${encodeURIComponent(row.sector)}`;
      const r = await fetch(url, { cache: "no-store" });
      const j = await r.json();
      if (j?.error) throw new Error(j.error);
      setOpenDetail(j as TickerDetail);
    } catch (e: any) {
      setOpenDetail({
        ...row,
        report: `Failed to load report: ${e?.message || "unknown error"}`,
      });
    } finally {
      setDetailLoading(false);
    }
  };

  const DetailModal = () => {
    const title = openDetail ? `${openDetail.ticker} · ${openDetail.sector}` : "Loading…";
    return (
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-end md:items-center justify-center p-4"
        onClick={closeDetail}
        role="presentation"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Ticker details"
          className="w-full max-w-5xl rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-[var(--border)] flex items-center gap-3">
            <div className="font-semibold text-[var(--text)]">{title}</div>
            <div className="flex-1" />
            <button
              onClick={closeDetail}
              className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
              title="Close (Esc)"
            >
              Close
            </button>
            <button
              onClick={closeDetail}
              className="p-2 rounded-lg hover:bg-white/5 text-[var(--text-dim)] hover:text-[var(--text)]"
              title="Close (Esc)"
              aria-label="Close dialog"
            >
              <X size={16} />
            </button>
          </div>

          <div className="p-4 max-h-[75vh] overflow-auto">
            {detailLoading && (
              <div className="text-[var(--text-dim)] text-sm flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                Loading full report…
              </div>
            )}

            {openDetail && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center gap-2 px-2 py-0.5 rounded-full border text-xs ${badgeClass(openDetail.signal)}`}>
                    <SignalIcon s={openDetail.signal} />
                    {openDetail.signal}
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    Score: <span className="font-mono text-[var(--text)]">{fmt(openDetail.score)}</span>
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    As of: <span className="font-mono text-[var(--text)]">{openDetail.as_of_date}</span>
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    Entry: <span className="font-mono text-[var(--text)]">{fmt(openDetail.entry?.entry_price)}</span>
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    Stop: <span className="font-mono text-[var(--text)]">{fmt(openDetail.risk?.stop_price)}</span>
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    T1: <span className="font-mono text-[var(--text)]">{fmt(openDetail.risk?.target_1)}</span>
                  </span>
                  <span className="text-xs text-[var(--text-dim)]">
                    T2: <span className="font-mono text-[var(--text)]">{fmt(openDetail.risk?.target_2)}</span>
                  </span>
                </div>

                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3">
                  <div className="text-xs text-[var(--text-dim)] mb-2">Phoenix Report</div>
                  <pre className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--text)] font-mono">
                    {openDetail.report || "No report text available."}
                  </pre>
                </div>
              </div>
            )}

            {!detailLoading && !openDetail && (
              <div className="text-[var(--text-dim)] text-sm">No detail loaded.</div>
            )}
          </div>

          <div className="px-4 py-3 border-t border-[var(--border)] flex items-center justify-end gap-2 bg-black/10">
            <button
              onClick={closeDetail}
              className="px-3 py-2 rounded-lg border border-[var(--border)] text-sm text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Client-only render prevents dev hydration mismatches during rapid iteration.
  // This page fetches its data client-side anyway.
  if (!mounted) {
    return <div className="min-h-screen bg-[var(--bg)]" />;
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-[var(--text-dim)] hover:text-[var(--text)] transition-colors text-sm">
            <ChevronLeft size={16} />
            Dashboard
          </Link>
          <div className="h-4 w-px bg-[var(--border)]" />
          <div className="text-sm font-semibold">Phoenix Sector Scans</div>
          <div className="flex-1" />
          <button
            onClick={refreshRuns}
            className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5 flex items-center gap-2"
            title="Refresh available runs"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-5">
        {err && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 px-4 py-3 text-sm">
            {err}
          </div>
        )}

        {/* Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-4">
            <div className="text-xs text-[var(--text-dim)] mb-2">Run</div>
            <div className="flex gap-2">
              <select
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              >
                {runs.length === 0 && <option value="">No runs found</option>}
                {runs.map((r) => (
                  <option key={r.date} value={r.date}>
                    {r.date}
                  </option>
                ))}
              </select>
              <button
                onClick={() => selectedDate && !compareMode && loadRun(selectedDate)}
                className="px-3 py-2 rounded-lg border border-[var(--border)] hover:bg-white/5"
                title={compareMode ? "Reload handled automatically in compare mode" : "Reload run"}
              >
                <ExternalLink size={16} />
              </button>
            </div>

            <div className="mt-3 flex items-center justify-between gap-3">
              <button
                onClick={() => setCompareMode((v) => !v)}
                className={`text-xs px-3 py-1.5 rounded-lg border ${
                  compareMode
                    ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-200"
                    : "border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
                }`}
                title="Compare two run dates (no future data beyond each run's cutoff)"
              >
                Compare runs
              </button>
              {compareMode && (
                <div className="flex items-center gap-2">
                  <div className="text-xs text-[var(--text-dim)]">Ext &gt;</div>
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    value={extensionThresholdPct}
                    onChange={(e) => setExtensionThresholdPct(Number(e.target.value))}
                    className="w-16 px-2 py-1 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg)] font-mono"
                    title="Mark as 'extended' when (entry - pivot)/pivot exceeds this %"
                  />
                  <div className="text-xs text-[var(--text-dim)]">%</div>
                </div>
              )}
            </div>

            {compareMode && (
              <div className="mt-3">
                <div className="text-xs text-[var(--text-dim)] mb-2">Compare to</div>
                <select
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                  value={compareDate}
                  onChange={(e) => setCompareDate(e.target.value)}
                >
                  <option value="">Select date…</option>
                  {runs
                    .filter((r) => r.date !== selectedDate)
                    .map((r) => (
                      <option key={r.date} value={r.date}>
                        {r.date}
                      </option>
                    ))}
                </select>
                <div className="mt-2 text-[11px] text-[var(--text-dim)]">
                  Base: <span className="font-mono text-[var(--text)]">{selectedDate || "—"}</span> · Compare:{" "}
                  <span className="font-mono text-[var(--text)]">{compareDate || "—"}</span>
                </div>
              </div>
            )}

            <div className="mt-3 text-xs text-[var(--text-dim)]">
              {data?.meta?.sectors?.length ? (
                <div>Universe: {data.meta.sectors.join(" · ")}</div>
              ) : (
                <div>Universe: —</div>
              )}
              <div>
                Analyzed: <span className="text-[var(--text)] font-semibold">{data?.meta?.results ?? "—"}</span>{" "}
                · Elapsed: <span className="text-[var(--text)] font-semibold">{fmt(data?.meta?.elapsed_sec)}s</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-4">
            <div className="text-xs text-[var(--text-dim)] mb-2">Filters</div>
            <div className="flex flex-wrap gap-2 items-center">
              <div className="relative flex-1 min-w-56">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-dim)]" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search ticker / stage / pattern…"
                  className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                />
              </div>
              <select
                className="px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
              >
                {sectors.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <select
                className="px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                value={signalFilter}
                onChange={(e) => setSignalFilter(e.target.value as any)}
              >
                <option value="All">All signals</option>
                <option value="BUY">BUY</option>
                <option value="WATCH">WATCH</option>
                <option value="AVOID">AVOID</option>
              </select>
              <button
                onClick={() => setOnlyPassed((p) => !p)}
                className={`px-3 py-2 text-sm rounded-lg border flex items-center gap-2 ${
                  onlyPassed
                    ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-200"
                    : "border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)]"
                }`}
                title="Only show tickers that passed hard filters"
              >
                <Filter size={14} />
                Passed
              </button>
              <button
                onClick={() => setSortBy((s) => (s === "score" ? "ticker" : "score"))}
                className="px-3 py-2 text-sm rounded-lg border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)]"
              >
                Sort: {sortBy === "score" ? "Score ↓" : "Ticker A–Z"}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-4">
            <div className="text-xs text-[var(--text-dim)] mb-2">Summary</div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <div className="text-xs text-[var(--text-dim)]">BUY</div>
                <div className="font-bold text-green-400">{stats.buy}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <div className="text-xs text-[var(--text-dim)]">WATCH</div>
                <div className="font-bold text-yellow-300">{stats.watch}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <div className="text-xs text-[var(--text-dim)]">AVOID</div>
                <div className="font-bold text-red-400">{stats.avoid}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                <div className="text-xs text-[var(--text-dim)]">Passed</div>
                <div className="font-bold text-indigo-300">{stats.pass}</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-[var(--text-dim)]">
              Showing{" "}
              <span className="text-[var(--text)] font-semibold">{compareMode ? compareRows.length : filtered.length}</span>{" "}
              of{" "}
              <span className="text-[var(--text)] font-semibold">{stats.total}</span>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border)] text-xs text-[var(--text-dim)] flex items-center justify-between">
            <div>
              {compareMode
                ? "Compare mode: values are shown for Base → Compare. Click a row to open the report for the selected Base run."
                : "Click a row to open the full Phoenix report (loaded on demand)."}
            </div>
            {loading && <div className="text-indigo-300">Loading…</div>}
          </div>
          <div className="overflow-auto">
            {!compareMode && (
              <table className="min-w-[1320px] w-full text-sm">
              <thead className="bg-white/3 text-[var(--text-dim)]">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Ticker</th>
                  <th className="text-left px-4 py-2 font-medium">Sector</th>
                  <th className="text-left px-4 py-2 font-medium">Signal</th>
                  <th className="text-right px-4 py-2 font-medium">Score</th>
                  <th className="text-left px-4 py-2 font-medium">Stage</th>
                  <th className="text-left px-4 py-2 font-medium">Pattern</th>
                  <th className="text-right px-4 py-2 font-medium">Entry</th>
                  <th className="text-right px-4 py-2 font-medium">Stop</th>
                  <th className="text-right px-4 py-2 font-medium">Target 1</th>
                  <th className="text-right px-4 py-2 font-medium">Target 2</th>
                  <th
                    className="text-right px-4 py-2 font-medium"
                    title="Exit price is not part of Phoenix scan snapshots (as-of date)."
                  >
                    Exit
                  </th>
                  <th className="text-right px-4 py-2 font-medium">Details</th>
                  <th className="text-left px-4 py-2 font-medium">Hard filter</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={`${r.sector}-${r.ticker}`}
                    className="border-t border-[var(--border)] hover:bg-white/5"
                  >
                    <td className="px-4 py-2 font-mono font-semibold text-[var(--text)]">{r.ticker}</td>
                    <td className="px-4 py-2 text-[var(--text-dim)]">{r.sector}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center gap-2 px-2 py-0.5 rounded-full border text-xs ${badgeClass(r.signal)}`}>
                        <SignalIcon s={r.signal} />
                        {r.signal}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-mono">{fmt(r.score)}</td>
                    <td className="px-4 py-2 text-[var(--text-dim)]">
                      {r.stage?.stage != null ? `Stage ${r.stage.stage} · ${r.stage.label ?? "—"}` : "—"}
                    </td>
                    <td className="px-4 py-2 text-[var(--text-dim)]">
                      {r.pattern?.pattern_name && r.pattern.pattern_name !== "None"
                        ? `${r.pattern.pattern_name}${r.pattern.confirmed ? " (confirmed)" : ""}`
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">{fmt(r.entry?.entry_price)}</td>
                    <td className="px-4 py-2 text-right font-mono">{fmt(r.risk?.stop_price)}</td>
                    <td className="px-4 py-2 text-right font-mono">{fmt(r.risk?.target_1)}</td>
                    <td className="px-4 py-2 text-right font-mono">{fmt(r.risk?.target_2)}</td>
                    <td className="px-4 py-2 text-right font-mono text-[var(--text-dim)]">—</td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => openTicker(r)}
                        className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
                        title="Open full Phoenix report"
                      >
                        Open
                      </button>
                    </td>
                    <td className="px-4 py-2 text-[var(--text-dim)]">
                      {r.hard_filter_passed ? (
                        <span className="text-green-400">PASS</span>
                      ) : (
                        <span className="text-red-400" title={r.hard_filter_reason ?? ""}>
                          FAIL
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={13} className="px-4 py-10 text-center text-[var(--text-dim)]">
                      No rows match your filters.
                    </td>
                  </tr>
                )}
              </tbody>
              </table>
            )}

            {compareMode && (
              <table className="min-w-[1420px] w-full text-sm">
                <thead className="bg-white/3 text-[var(--text-dim)]">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium">Ticker</th>
                    <th className="text-left px-4 py-2 font-medium">Sector</th>
                    <th className="text-left px-4 py-2 font-medium">Status</th>
                    <th className="text-left px-4 py-2 font-medium">Signal</th>
                    <th className="text-right px-4 py-2 font-medium">Score</th>
                    <th className="text-right px-4 py-2 font-medium">Entry</th>
                    <th className="text-right px-4 py-2 font-medium">Stop</th>
                    <th className="text-right px-4 py-2 font-medium">T1</th>
                    <th className="text-right px-4 py-2 font-medium">T2</th>
                    <th className="text-right px-4 py-2 font-medium" title="(entry - pivot)/pivot using each run's own pivot + entry">
                      Ext%
                    </th>
                    <th className="text-left px-4 py-2 font-medium">Extended?</th>
                  </tr>
                </thead>
                <tbody>
                  {compareRows.map((r) => {
                    const show = (x: ResultRow | null | undefined) => x ?? null;
                    const b = show(r.base);
                    const c = show(r.comp);
                    const sig = (c?.signal || b?.signal) as PhoenixSignal | undefined;
                    const score = c?.score ?? b?.score;

                    const statusClass =
                      r.status === "New"
                        ? "bg-green-500/10 border-green-500/30 text-green-300"
                        : r.status === "Dropped"
                          ? "bg-red-500/10 border-red-500/30 text-red-300"
                          : "bg-white/5 border-[var(--border)] text-[var(--text-dim)]";

                    const extDisplay = `${fmtPct(r.baseExtPct)} → ${fmtPct(r.compExtPct)}`;
                    const extendedDisplay = `${r.baseExtended ? "YES" : "no"} → ${r.compExtended ? "YES" : "no"}`;

                    return (
                      <tr
                        key={r.key}
                        className="border-t border-[var(--border)] hover:bg-white/5"
                        onClick={() => {
                          // In compare mode, open detail for the base run (selectedDate) for consistency.
                          const row = b || c;
                          if (row) openTicker(row);
                        }}
                        title="Click to open the Phoenix report (Base run)"
                      >
                        <td className="px-4 py-2 font-mono font-semibold text-[var(--text)]">{r.ticker}</td>
                        <td className="px-4 py-2 text-[var(--text-dim)]">{r.sector}</td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs ${statusClass}`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          {sig ? (
                            <span className={`inline-flex items-center gap-2 px-2 py-0.5 rounded-full border text-xs ${badgeClass(sig)}`}>
                              <SignalIcon s={sig} />
                              {b?.signal ?? "—"} → {c?.signal ?? "—"}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">
                          {fmt(b?.score)} → {fmt(score)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">
                          {fmt(b?.entry?.entry_price)} → {fmt(c?.entry?.entry_price)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">
                          {fmt(b?.risk?.stop_price)} → {fmt(c?.risk?.stop_price)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">
                          {fmt(b?.risk?.target_1)} → {fmt(c?.risk?.target_1)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">
                          {fmt(b?.risk?.target_2)} → {fmt(c?.risk?.target_2)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono">{extDisplay}</td>
                        <td className="px-4 py-2 text-[var(--text-dim)] font-mono">{extendedDisplay}</td>
                      </tr>
                    );
                  })}
                  {compareRows.length === 0 && (
                    <tr>
                      <td colSpan={11} className="px-4 py-10 text-center text-[var(--text-dim)]">
                        Select a “Compare to” date to view differences.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Detail modal */}
      {(detailLoading || openDetail) && <DetailModal />}
    </div>
  );
}

