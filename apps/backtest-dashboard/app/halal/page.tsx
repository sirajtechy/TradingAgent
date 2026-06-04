"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  RefreshCw,
  Wifi,
  WifiOff,
} from "lucide-react";

// ── types ────────────────────────────────────────────────────────────
interface Pattern {
  name: string;
  direction: string;
  confidence: number;
  formation_start: string;
  formation_end: string;
  breakout_confirmed: boolean;
  volume_confirmation: boolean;
  breakout_price: number | null;
  breakout_date: string | null;
  pattern_target: number | null;
  description: string;
}

interface Trade {
  entry_date: string;
  entry_price: number;
  entry_source: string;
  exit_date: string;
  exit_price: number;
  exit_outcome: string;
  holding_days: number;
  stop_loss: number;
  target_price: number;
  gross_profit_pct: number;
  net_profit_pct: number;
  risk_pct: number;
  reward_risk_ratio: number;
  atr_at_entry: number;
  adx_at_entry: number;
  rsi_at_entry: number;
  estimated_days_to_target?: number;
  estimated_target_window?: string;
  estimated_target_date?: string;
}

interface Prediction {
  ticker: string;
  sector: string;
  cutoff_date: string;
  target_days_requested: number;
  sentiment: "bullish" | "bearish" | "neutral";
  confidence_score: number;
  confidence_pct: number;
  tech_score: number;
  fund_score: number;
  fusion_weights: { tech: number; fund: number };
  conflict_detected: boolean;
  conflict_resolution: string | null;
  patterns: Pattern[];
  signal_alignment: {
    signal_count: number;
    bullish_frameworks: number;
    entry_rules_met: number;
    confidence_pct: number;
    confidence_label: string;
  };
  orchestrator_score: number;
  orchestrator_confidence: number;
  trade: Trade | null;
  no_trade_reason: string | null;
}

interface ApiData {
  meta: {
    date: string;
    totalTickers: number;
    targetDays: number;
    lastUpdated?: string;
  };
  predictions: Prediction[];
}

// ── normalize ────────────────────────────────────────────────────────
function normalize(raw: Partial<Prediction>): Prediction {
  return {
    ticker: raw.ticker ?? "???",
    sector: raw.sector ?? "Unknown",
    cutoff_date: raw.cutoff_date ?? "",
    target_days_requested: raw.target_days_requested ?? 0,
    sentiment: raw.sentiment ?? "neutral",
    confidence_score: raw.confidence_score ?? 0,
    confidence_pct: raw.confidence_pct ?? 0,
    tech_score: raw.tech_score ?? 0,
    fund_score: raw.fund_score ?? 0,
    fusion_weights: raw.fusion_weights ?? { tech: 0, fund: 0 },
    conflict_detected: raw.conflict_detected ?? false,
    conflict_resolution: raw.conflict_resolution ?? null,
    patterns: raw.patterns ?? [],
    signal_alignment: raw.signal_alignment ?? {
      signal_count: 0,
      bullish_frameworks: 0,
      entry_rules_met: 0,
      confidence_pct: 0,
      confidence_label: "none",
    },
    orchestrator_score: raw.orchestrator_score ?? 0,
    orchestrator_confidence: raw.orchestrator_confidence ?? 0,
    trade: raw.trade ?? null,
    no_trade_reason: raw.no_trade_reason ?? null,
  };
}

// ── helpers ──────────────────────────────────────────────────────────
type SortKey =
  | "ticker"
  | "sentiment"
  | "confidence_score"
  | "tech_score"
  | "fund_score"
  | "orchestrator_score"
  | "sector";

function SentimentBadge({ s }: { s: string }) {
  const cls =
    s === "bullish"
      ? "bg-green-500/20 text-green-400 border-green-500/40"
      : s === "bearish"
      ? "bg-red-500/20 text-red-400 border-red-500/40"
      : "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
  const Icon = s === "bullish" ? TrendingUp : s === "bearish" ? TrendingDown : Minus;
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-semibold ${cls}`}>
      <Icon size={12} />
      {s.toUpperCase()}
    </span>
  );
}

function ScoreBar({ value }: { value: number }) {
  const pct = Math.min(100, value);
  const color = value >= 65 ? "bg-green-500" : value >= 45 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono">{value.toFixed(1)}</span>
    </div>
  );
}

function PatternTag({ p }: { p: Pattern }) {
  const cls =
    p.direction === "bullish"
      ? "bg-green-500/10 text-green-400 border-green-500/30"
      : "bg-red-500/10 text-red-400 border-red-500/30";
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${cls}`}>
      {p.name}
      <span className="opacity-60">{(p.confidence * 100).toFixed(0)}%</span>
      {p.breakout_confirmed && <span className="text-[8px]">✓BO</span>}
    </span>
  );
}

function DetailPanel({ p }: { p: Prediction }) {
  return (
    <div className="px-4 py-4 bg-[#0d0d14] space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Scores */}
        <div className="space-y-2">
          <h4 className="text-[10px] uppercase tracking-wider text-[#8888a0]">Scores & Weights</h4>
          <div className="space-y-1.5 text-xs">
            {[
              ["Tech Score", `${p.tech_score.toFixed(1)} (${(p.fusion_weights.tech * 100).toFixed(0)}%w)`],
              ["Fund Score", `${p.fund_score.toFixed(1)} (${(p.fusion_weights.fund * 100).toFixed(0)}%w)`],
              ["Orchestrator", p.orchestrator_score.toFixed(1)],
              ["Confidence", `${p.confidence_pct.toFixed(1)}%`],
              ["Signal Align", `${p.signal_alignment.bullish_frameworks}/${p.signal_alignment.signal_count} bullish`],
              ["Entry Rules", String(p.signal_alignment.entry_rules_met)],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between">
                <span className="text-[#8888a0]">{label}</span>
                <span className="font-mono">{val}</span>
              </div>
            ))}
            {p.conflict_detected && (
              <div className="mt-2 px-2 py-1.5 rounded bg-orange-500/10 border border-orange-500/30 text-orange-400 text-[11px]">
                ⚠ Conflict: {p.conflict_resolution || "unresolved"}
              </div>
            )}
          </div>
        </div>

        {/* Trade */}
        <div className="space-y-2">
          <h4 className="text-[10px] uppercase tracking-wider text-[#8888a0]">Trade Setup</h4>
          {p.trade ? (
            <div className="space-y-1.5 text-xs">
              {[
                ["Entry", `$${p.trade.entry_price.toFixed(2)} on ${p.trade.entry_date}`],
                ["Exit", p.trade.exit_outcome === "OPEN" ? "Pending (live setup)" : `$${p.trade.exit_price.toFixed(2)} on ${p.trade.exit_date}`],
                ["Target", `$${p.trade.target_price.toFixed(2)}`],
                ...(p.trade.exit_outcome === "OPEN" && p.trade.estimated_target_date ? [["Est. Target Date", `${p.trade.estimated_target_date} (${p.trade.estimated_target_window})`]] as [string, string][] : []),
                ["Stop Loss", `$${p.trade.stop_loss.toFixed(2)}`],
                ["R:R", `${p.trade.reward_risk_ratio?.toFixed(1) ?? "—"}:1`],
                ["Hold", p.trade.exit_outcome === "OPEN" ? `~${p.trade.estimated_days_to_target ?? "?"} days (est.)` : `${p.trade.holding_days}d`],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[#8888a0]">{label}</span>
                  <span className="font-mono">{val}</span>
                </div>
              ))}
              <div className="flex justify-between">
                <span className="text-[#8888a0]">Outcome</span>
                <span className={`font-mono font-bold ${
                  p.trade.exit_outcome === "HIT_TARGET" ? "text-green-400"
                  : p.trade.exit_outcome === "HIT_STOP" ? "text-red-400"
                  : p.trade.exit_outcome === "OPEN" ? "text-cyan-400"
                  : "text-yellow-400"
                }`}>
                  {p.trade.exit_outcome === "OPEN" ? "⏳ OPEN" : p.trade.exit_outcome}
                </span>
              </div>
              {p.trade.exit_outcome !== "OPEN" && (
                <div className="flex justify-between">
                  <span className="text-[#8888a0]">P/L</span>
                  <span className={`font-mono font-bold ${p.trade.net_profit_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {p.trade.net_profit_pct >= 0 ? "+" : ""}{p.trade.net_profit_pct.toFixed(2)}%
                  </span>
                </div>
              )}
              <div className="text-[10px] text-[#8888a0] mt-1">via {p.trade.entry_source}</div>
            </div>
          ) : (
            <p className="text-xs text-[#8888a0] italic">{p.no_trade_reason || "No trade generated"}</p>
          )}
        </div>

        {/* Patterns */}
        <div className="space-y-2">
          <h4 className="text-[10px] uppercase tracking-wider text-[#8888a0]">Patterns ({p.patterns.length})</h4>
          <div className="space-y-1 max-h-52 overflow-y-auto">
            {[...p.patterns].sort((a, b) => b.confidence - a.confidence).map((pat, i) => (
              <div key={i} className={`text-[11px] px-2 py-1.5 rounded border ${pat.direction === "bullish" ? "bg-green-500/5 border-green-500/20" : "bg-red-500/5 border-red-500/20"}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">{pat.name}</span>
                  <span className="font-mono text-[10px]">{(pat.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="text-[10px] text-[#8888a0] mt-0.5">{pat.description}</div>
                <div className="flex gap-2 mt-0.5 text-[10px]">
                  {pat.breakout_confirmed && <span className="text-green-400">✓ Breakout</span>}
                  {pat.volume_confirmation && <span className="text-cyan-400">✓ Volume</span>}
                  {pat.pattern_target != null && <span className="text-[#8888a0]">Target: ${pat.pattern_target.toFixed(2)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function PulseDot() {
  return (
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
    </span>
  );
}

// ── main page ────────────────────────────────────────────────────────
const POLL_MS = 10_000;

export default function HalalPredictions() {
  const [data, setData] = useState<ApiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [prevCount, setPrevCount] = useState(0);
  const [flash, setFlash] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [sectorFilter, setSectorFilter] = useState("all");
  const [sentimentFilter, setSentimentFilter] = useState("all");
  const [tradeFilter, setTradeFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("confidence_score");
  const [sortAsc, setSortAsc] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/halal-predictions", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: ApiData = await res.json();
      const normalized: ApiData = { ...json, predictions: (json.predictions ?? []).map(normalize) };
      setData((prev) => {
        const newCount = normalized.predictions.length;
        if (prev && newCount !== prev.predictions.length) {
          setPrevCount(prev.predictions.length);
          setFlash(true);
          setTimeout(() => setFlash(false), 3000);
        }
        return normalized;
      });
      setError(null);
      setLastFetched(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fetch failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, POLL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchData]);

  const predictions = data?.predictions ?? [];

  const sectors = useMemo(() => [...new Set(predictions.map((p) => p.sector))].sort(), [predictions]);

  const filtered = useMemo(() => {
    let list = predictions;
    if (sectorFilter !== "all") list = list.filter((p) => p.sector === sectorFilter);
    if (sentimentFilter !== "all") list = list.filter((p) => p.sentiment === sentimentFilter);
    if (tradeFilter === "has_trade") list = list.filter((p) => p.trade !== null);
    else if (tradeFilter === "no_trade") list = list.filter((p) => p.trade === null);
    if (search) { const q = search.toUpperCase(); list = list.filter((p) => p.ticker.includes(q)); }
    return [...list].sort((a, b) => {
      const av = (a as unknown as Record<string, unknown>)[sortKey] ?? "";
      const bv = (b as unknown as Record<string, unknown>)[sortKey] ?? "";
      if (typeof av === "string" && typeof bv === "string")
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [predictions, sectorFilter, sentimentFilter, tradeFilter, search, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (sortAsc ? <ChevronUp size={10} className="inline" /> : <ChevronDown size={10} className="inline" />) : null;

  const bullish = predictions.filter((p) => p.sentiment === "bullish").length;
  const bearish = predictions.filter((p) => p.sentiment === "bearish").length;
  const neutral = predictions.filter((p) => p.sentiment === "neutral").length;
  const withTrades = predictions.filter((p) => p.trade !== null).length;
  const avgScore = predictions.length > 0 ? predictions.reduce((s, p) => s + p.orchestrator_score, 0) / predictions.length : 0;
  const conflicts = predictions.filter((p) => p.conflict_detected).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center space-y-3">
          <RefreshCw size={28} className="text-indigo-400 animate-spin mx-auto" />
          <p className="text-sm text-[#8888a0]">Loading predictions…</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center space-y-3">
          <WifiOff size={28} className="text-red-400 mx-auto" />
          <p className="text-sm text-red-400">{error}</p>
          <p className="text-xs text-[#8888a0]">Make sure the watcher is running and has written halal-predictions.json</p>
          <button onClick={fetchData} className="mt-2 text-xs px-4 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const meta = data!.meta;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e4e4ef]">
      <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">Halal Predictions</h1>
              <PulseDot />
              <span className="text-[10px] text-green-400 font-semibold">LIVE</span>
            </div>
            <p className="text-sm text-[#8888a0]">
              {meta.date} · {predictions.length} tickers · {meta.targetDays}-day horizon
            </p>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-[#8888a0]">
              {error ? <WifiOff size={12} className="text-red-400" /> : <Wifi size={12} className="text-green-400" />}
              {lastFetched && <span>Updated {lastFetched.toLocaleTimeString()} · every {POLL_MS / 1000}s</span>}
              <button onClick={fetchData} title="Refresh now" className="ml-1 p-1 rounded hover:bg-white/10">
                <RefreshCw size={12} />
              </button>
            </div>
            <a href="/" className="text-xs text-indigo-400 hover:underline">← Dashboard</a>
          </div>
        </div>

        {/* Flash banner */}
        {flash && (
          <div className="px-4 py-2 rounded-lg bg-green-500/15 border border-green-500/40 text-green-400 text-sm animate-pulse">
            ✦ {predictions.length - prevCount > 0 ? `+${predictions.length - prevCount}` : "Data"} new ticker{predictions.length - prevCount !== 1 ? "s" : ""} added — now {predictions.length} total
          </div>
        )}

        {/* KPI */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {[
            { label: "Bullish", val: bullish, cls: "border-green-500/30 bg-green-500/10 text-green-400" },
            { label: "Bearish", val: bearish, cls: "border-red-500/30 bg-red-500/10 text-red-400" },
            { label: "Neutral", val: neutral, cls: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400" },
            { label: "Trades", val: withTrades, cls: "border-[#1e1e2e] bg-[#111118] text-[#e4e4ef]" },
            { label: "Avg Score", val: avgScore.toFixed(1), cls: "border-[#1e1e2e] bg-[#111118] text-[#e4e4ef]" },
            { label: "Conflicts", val: conflicts, cls: "border-[#1e1e2e] bg-[#111118] text-[#e4e4ef]" },
          ].map(({ label, val, cls }) => (
            <div key={label} className={`rounded-lg border px-3 py-2 ${cls}`}>
              <p className="text-[10px] text-[#8888a0] uppercase">{label}</p>
              <p className="text-xl font-bold font-mono">{val}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Filter size={14} className="text-[#8888a0]" />
          <select value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} className="text-xs bg-[#111118] border border-[#1e1e2e] rounded-lg px-3 py-1.5 text-[#e4e4ef]">
            <option value="all">All Sectors</option>
            {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={sentimentFilter} onChange={(e) => setSentimentFilter(e.target.value)} className="text-xs bg-[#111118] border border-[#1e1e2e] rounded-lg px-3 py-1.5 text-[#e4e4ef]">
            <option value="all">All Sentiments</option>
            <option value="bullish">Bullish</option>
            <option value="bearish">Bearish</option>
            <option value="neutral">Neutral</option>
          </select>
          <select value={tradeFilter} onChange={(e) => setTradeFilter(e.target.value)} className="text-xs bg-[#111118] border border-[#1e1e2e] rounded-lg px-3 py-1.5 text-[#e4e4ef]">
            <option value="all">All (Trade / No Trade)</option>
            <option value="has_trade">Has Trade</option>
            <option value="no_trade">No Trade</option>
          </select>
          {/* Tech sort button */}
          <button
            onClick={() => toggleSort("tech_score")}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              sortKey === "tech_score"
                ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-300"
                : "bg-[#111118] border-[#1e1e2e] text-[#8888a0] hover:text-[#e4e4ef]"
            }`}
          >
            Tech
            {sortKey === "tech_score" ? (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />) : <ChevronDown size={12} className="opacity-30" />}
          </button>
          {/* Fund sort button */}
          <button
            onClick={() => toggleSort("fund_score")}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              sortKey === "fund_score"
                ? "bg-purple-500/20 border-purple-500/50 text-purple-300"
                : "bg-[#111118] border-[#1e1e2e] text-[#8888a0] hover:text-[#e4e4ef]"
            }`}
          >
            Fund
            {sortKey === "fund_score" ? (sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />) : <ChevronDown size={12} className="opacity-30" />}
          </button>
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8888a0]" />
            <input type="text" placeholder="Ticker…" value={search} onChange={(e) => setSearch(e.target.value)} className="text-xs bg-[#111118] border border-[#1e1e2e] rounded-lg pl-8 pr-3 py-1.5 text-[#e4e4ef] w-36" />
          </div>
          <span className="text-xs text-[#8888a0] ml-auto">{filtered.length} results</span>
        </div>

        {/* Table */}
        <div className={`rounded-xl border bg-[#111118] overflow-hidden transition-colors duration-700 ${flash ? "border-green-500/50" : "border-[#1e1e2e]"}`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#1e1e2e] text-[#8888a0]">
                  <th className="w-8 px-2 py-2.5" />
                  {([["ticker","Ticker"],["sector","Sector"],["sentiment","Signal"],["confidence_score","Score"],["tech_score","Tech"],["fund_score","Fund"]] as [SortKey,string][]).map(([k,label]) => (
                    <th key={k} onClick={() => toggleSort(k)} className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[#e4e4ef] select-none">
                      {label} <SortIcon k={k} />
                    </th>
                  ))}
                  <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider">Patterns</th>
                  <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider">Trade</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <Fragment key={p.ticker}>
                    <tr
                      onClick={() => setExpanded(expanded === p.ticker ? null : p.ticker)}
                      className={`border-b border-[#1e1e2e]/50 cursor-pointer transition-colors ${expanded === p.ticker ? "bg-indigo-500/5" : "hover:bg-white/[0.02]"}`}
                    >
                      <td className="px-2 py-2.5 text-[#8888a0]">
                        <ChevronRight size={14} className={`transition-transform ${expanded === p.ticker ? "rotate-90" : ""}`} />
                      </td>
                      <td className="px-3 py-2.5 font-mono font-bold">{p.ticker}</td>
                      <td className="px-3 py-2.5 text-xs text-[#8888a0]">{p.sector}</td>
                      <td className="px-3 py-2.5"><SentimentBadge s={p.sentiment} /></td>
                      <td className="px-3 py-2.5"><ScoreBar value={p.confidence_score} /></td>
                      <td className="px-3 py-2.5"><ScoreBar value={p.tech_score} /></td>
                      <td className="px-3 py-2.5"><ScoreBar value={p.fund_score} /></td>
                      <td className="px-3 py-2.5">
                        <div className="flex flex-wrap gap-1 max-w-[240px]">
                          {p.patterns.filter((x) => x.confidence >= 0.5).sort((a, b) => b.confidence - a.confidence).slice(0, 3).map((pat, i) => <PatternTag key={i} p={pat} />)}
                          {p.patterns.filter((x) => x.confidence >= 0.5).length > 3 && (
                            <span className="text-[10px] text-[#8888a0]">+{p.patterns.filter((x) => x.confidence >= 0.5).length - 3}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        {p.trade ? (
                          p.trade.exit_outcome === "OPEN" ? (
                            <span className="text-xs font-mono font-bold text-cyan-400">⏳ OPEN</span>
                          ) : (
                            <span className={`text-xs font-mono font-bold ${p.trade.net_profit_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {p.trade.net_profit_pct >= 0 ? "+" : ""}{p.trade.net_profit_pct.toFixed(1)}%
                            </span>
                          )
                        ) : (
                          <span className="text-[10px] text-[#8888a0]">—</span>
                        )}
                      </td>
                    </tr>
                    {expanded === p.ticker && (
                      <tr><td colSpan={9}><DetailPanel p={p} /></td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer hint */}
        <p className="text-[10px] text-[#8888a0] text-center">
          Auto-refreshes every {POLL_MS / 1000}s · Run{" "}
          <code className="font-mono bg-white/5 px-1 rounded">
            python3 scripts/watch_halal_predictions.py --input-dir data/output/predictions/halal_2026-04-04
          </code>{" "}
          to push live updates
        </p>
      </div>
    </div>
  );
}
