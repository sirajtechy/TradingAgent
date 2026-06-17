"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  Brain,
  Loader2,
  Microscope,
  Play,
  ShoppingCart,
  Eye,
} from "lucide-react";
import {
  AGENT_ORDER,
  AnalyzeAgentGrid,
  AnalyzeDoc,
  FusionHero,
  SignalPill,
  defaultYesterday,
  scoreColor,
} from "../analyzeUi";

type WatchlistRow = {
  ticker: string;
  phoenix_signal: string;
  sector: string;
  phoenix_score?: number | null;
  analyze_cached?: boolean;
  analyze_path?: string | null;
  advisory_verdict?: string | null;
  orchestrator_score?: number | null;
  news_one_liner?: string | null;
  news_headline_count?: number;
};

type WatchlistResponse = {
  ok?: boolean;
  error?: string;
  as_of_date?: string;
  meta?: {
    signal_date?: string;
    source_path?: string;
    buy_count?: number;
    watch_count?: number;
    total?: number;
    analyzed_count?: number;
  };
  tickers?: WatchlistRow[];
};

export default function WatchlistAnalyzePage() {
  const [date, setDate] = useState("");
  const [tradeFocus, setTradeFocus] = useState(false);
  const [loading, setLoading] = useState(true);
  const [batchLoading, setBatchLoading] = useState(false);
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState("phoenix");
  const [analyzeDoc, setAnalyzeDoc] = useState<AnalyzeDoc | null>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);

  const loadWatchlist = useCallback(() => {
    setLoading(true);
    setErr(null);
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    if (tradeFocus) params.set("trade_focus", "1");
    fetch(`/api/analyze/watchlist?${params}`)
      .then(async (r) => {
        const d = (await r.json()) as WatchlistResponse;
        if (!r.ok || d.error) throw new Error(d.error ?? "Failed to load watchlist");
        setData(d);
        if (!selectedTicker && d.tickers?.length) {
          setSelectedTicker(d.tickers[0].ticker);
        }
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Failed to load watchlist"))
      .finally(() => setLoading(false));
  }, [date, tradeFocus, selectedTicker]);

  useEffect(() => {
    loadWatchlist();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, tradeFocus]);

  useEffect(() => {
    if (!selectedTicker || !data?.as_of_date) {
      setAnalyzeDoc(null);
      return;
    }
    setAnalyzeLoading(true);
    fetch(
      `/api/analyze?ticker=${encodeURIComponent(selectedTicker)}&date=${encodeURIComponent(data.as_of_date)}&fusion=full`,
    )
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok || d.error) throw new Error(d.error ?? "No analysis");
        setAnalyzeDoc(d.doc ?? null);
      })
      .catch(() => setAnalyzeDoc(null))
      .finally(() => setAnalyzeLoading(false));
  }, [selectedTicker, data?.as_of_date]);

  const runBatch = () => {
    setBatchLoading(true);
    fetch("/api/analyze/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: data?.as_of_date || date || undefined,
        trade_focus: tradeFocus,
        force: false,
      }),
    })
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok || d.error) throw new Error(d.error ?? "Batch failed");
        loadWatchlist();
        if (selectedTicker) {
          fetch(
            `/api/analyze?ticker=${encodeURIComponent(selectedTicker)}&date=${encodeURIComponent(data?.as_of_date || date)}&fusion=full&source=run&refresh_context=1`,
          )
            .then((r) => r.json())
            .then((d) => setAnalyzeDoc(d.doc ?? null));
        }
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Batch failed"))
      .finally(() => setBatchLoading(false));
  };

  const rows = data?.tickers ?? [];
  const selectedRow = rows.find((r) => r.ticker === selectedTicker);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-4 md:px-8">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <Link href="/research/analyze" className="text-[var(--text-dim)] hover:text-[var(--text)]">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Microscope size={22} className="text-indigo-400" />
            BUY / WATCH deep dive
          </h1>
        </div>
      </header>

      <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
        <p className="text-sm text-[var(--text-dim)]">
          Full fusion breakdown for every Phoenix BUY and WATCH ticker from the latest{" "}
          <code className="text-emerald-400/90">master_pilot.json</code>. Batch CLI:{" "}
          <code className="text-emerald-400/90">
            ./bin/mts analyze --watchlist --fusion full --export-breakdown --refresh-context
          </code>
        </p>

        <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 flex flex-wrap gap-3 items-end">
          <label className="space-y-1">
            <span className="text-xs text-[var(--text-dim)]">Signal date</span>
            <input
              type="date"
              className="block bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              placeholder={defaultYesterday()}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--text-dim)] pb-2">
            <input type="checkbox" checked={tradeFocus} onChange={(e) => setTradeFocus(e.target.checked)} />
            Trade focus (BUY + WATCH score &gt; 60)
          </label>
          <button
            type="button"
            onClick={loadWatchlist}
            className="px-3 py-2 rounded-lg border border-[var(--border)] text-sm hover:bg-[var(--bg)]"
          >
            Refresh list
          </button>
          <button
            type="button"
            disabled={batchLoading || rows.length === 0}
            onClick={runBatch}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-50"
          >
            {batchLoading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            Analyze all missing
          </button>
        </section>

        {err && <p className="text-red-400 text-sm">{err}</p>}

        {data?.meta && (
          <div className="flex flex-wrap gap-4 text-sm">
            <span>
              <ShoppingCart size={14} className="inline text-emerald-400 mr-1" />
              BUY: <strong>{data.meta.buy_count ?? 0}</strong>
            </span>
            <span>
              <Eye size={14} className="inline text-amber-400 mr-1" />
              WATCH: <strong>{data.meta.watch_count ?? 0}</strong>
            </span>
            <span>
              Analyzed:{" "}
              <strong>
                {data.meta.analyzed_count ?? 0}/{data.meta.total ?? 0}
              </strong>
            </span>
            {data.meta.source_path && (
              <code className="text-xs text-[var(--text-dim)]">{data.meta.source_path}</code>
            )}
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-[var(--text-dim)] py-8">
            <Loader2 className="animate-spin" size={18} />
            Loading BUY/WATCH book…
          </div>
        )}

        {!loading && rows.length === 0 && (
          <p className="text-amber-400 text-sm">
            No BUY/WATCH tickers found. Run <code>./bin/mts daily</code> or pick a different signal date.
          </p>
        )}

        {rows.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-[minmax(280px,360px)_1fr] gap-4">
            <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-1">
              {rows.map((row) => {
                const active = selectedTicker === row.ticker;
                const px = row.phoenix_signal;
                return (
                  <button
                    key={row.ticker}
                    type="button"
                    onClick={() => setSelectedTicker(row.ticker)}
                    className={`w-full text-left rounded-lg border p-3 transition-colors ${
                      active
                        ? "border-indigo-500/50 bg-indigo-500/10"
                        : "border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg)]/80"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">{row.ticker}</span>
                      <span
                        className={`text-[10px] uppercase px-1.5 py-0.5 rounded ${
                          px === "BUY"
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {px}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--text-dim)] mt-1 truncate">{row.sector}</div>
                    <div className="flex items-center gap-2 mt-2 text-xs">
                      <span className={scoreColor(row.phoenix_score ?? null)}>
                        Phoenix {row.phoenix_score ?? "—"}
                      </span>
                      {row.analyze_cached ? (
                        <>
                          <SignalPill signal={row.advisory_verdict} />
                          <span className="text-emerald-400/80">ready</span>
                        </>
                      ) : (
                        <span className="text-amber-400">needs analyze</span>
                      )}
                    </div>
                    {row.news_one_liner && (
                      <p className="text-[11px] text-[var(--text-dim)] mt-2 line-clamp-2">{row.news_one_liner}</p>
                    )}
                  </button>
                );
              })}
            </div>

            <div className="space-y-4 min-w-0">
              {!selectedTicker && <p className="text-[var(--text-dim)]">Select a ticker</p>}
              {selectedTicker && analyzeLoading && (
                <div className="flex items-center gap-2 text-[var(--text-dim)] py-8">
                  <Loader2 className="animate-spin" size={18} />
                  Loading {selectedTicker} analysis…
                </div>
              )}
              {selectedTicker && !analyzeLoading && !analyzeDoc && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
                  <p>No cached analysis for {selectedTicker}.</p>
                  <p className="mt-2 text-[var(--text-dim)]">
                    Run{" "}
                    <code>
                      ./bin/mts analyze --ticker {selectedTicker} --date {data?.as_of_date} --fusion full
                      --export-breakdown
                    </code>{" "}
                    or click Analyze all missing.
                  </p>
                </div>
              )}
              {analyzeDoc && (
                <>
                  <FusionHero doc={analyzeDoc} fusion={analyzeDoc.fusion} />
                  {analyzeDoc.agent_breakdown && (
                    <section className="space-y-3">
                      <h2 className="text-sm font-medium flex items-center gap-2">
                        <Brain size={16} className="text-indigo-400" />
                        Agent intelligence — {selectedTicker}
                        {selectedRow && (
                          <span className="text-[var(--text-dim)] font-normal">
                            ({selectedRow.phoenix_signal} · {selectedRow.sector})
                          </span>
                        )}
                      </h2>
                      <AnalyzeAgentGrid
                        doc={analyzeDoc}
                        selectedAgent={selectedAgent}
                        onSelectAgent={setSelectedAgent}
                      />
                    </section>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
