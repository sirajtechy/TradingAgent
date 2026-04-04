"use client";

import { useMemo, useState } from "react";
import type { PredictionData, Prediction } from "../lib/types";
import { ChevronDown, ChevronUp, Filter, Search } from "lucide-react";

interface Props {
  predictions: PredictionData;
  sectors: string[];
  onTickerClick: (t: string) => void;
}

type SortKey =
  | "ticker"
  | "sector"
  | "signalLabel"
  | "orchestratorScore"
  | "confidence"
  | "profitPct"
  | "targetPrice"
  | "entryDate";

function SignalBadge({ signal }: { signal: string }) {
  const cls =
    signal === "BUY"
      ? "bg-green-500/20 text-green-400 border-green-500/40"
      : signal === "SELL"
      ? "bg-red-500/20 text-red-400 border-red-500/40"
      : "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${cls}`}>
      {signal}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-[var(--text-dim)]">{pct}%</span>
    </div>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const cls =
    sentiment === "bullish"
      ? "bg-green-500/20 text-green-400 border-green-500/40"
      : sentiment === "bearish"
      ? "bg-red-500/20 text-red-400 border-red-500/40"
      : "bg-yellow-500/20 text-yellow-400 border-yellow-500/40";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold capitalize ${cls}`}>
      {sentiment}
    </span>
  );
}

function formatDate(d: string | null) {
  if (!d) return "—";
  try {
    const dt = new Date(d + "T00:00:00");
    return dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return d;
  }
}

function ExpandedRow({ p, onTickerClick }: { p: Prediction; onTickerClick: (t: string) => void }) {
  return (
    <tr>
      <td colSpan={12} className="px-4 py-4 bg-[var(--bg)]/50">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Navigation */}
          <div className="space-y-3">
            <button
              onClick={() => onTickerClick(p.ticker)}
              className="text-indigo-400 hover:underline text-sm font-semibold"
            >
              View Full Detail →
            </button>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Last Known Price</span>
                <span className="font-mono">${p.lastPrice?.toFixed(2) ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Conviction</span>
                <span className="font-mono">{p.conviction}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Holding Days</span>
                <span className="font-mono">{p.holdingDays ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Peak Return</span>
                <span className={`font-mono ${(p.peakReturnPct ?? 0) > 0 ? "text-green-400" : "text-red-400"}`}>
                  {p.peakReturnPct != null ? `${p.peakReturnPct > 0 ? "+" : ""}${p.peakReturnPct.toFixed(1)}%` : "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="space-y-3">
            <p className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-2">
              Historical Performance
            </p>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Win Rate</span>
                <span className="font-mono">{p.winRatePct != null ? `${p.winRatePct.toFixed(0)}%` : "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Target Hit Probability</span>
                <span className="font-mono">{p.targetHitProbPct != null ? `${p.targetHitProbPct.toFixed(0)}%` : "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Max Drawdown</span>
                <span className="font-mono text-red-400">{p.maxDrawdownPct != null ? `${p.maxDrawdownPct.toFixed(1)}%` : "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Seasonal Match</span>
                <span className="font-mono">{p.seasonalMatch ? "✅ Yes" : "❌ No"}</span>
              </div>
            </div>
          </div>

          {/* Weight Info */}
          <div className="space-y-3">
            <p className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-2">
              Model Weights
            </p>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Tech Weight</span>
                <span className="font-mono">{(p.weightTech * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Fund Weight</span>
                <span className="font-mono">{(p.weightFund * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-dim)]">Bull Probability</span>
                <span className="font-mono">{p.orchestratorScore.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function PredictionsTable({ predictions, sectors, onTickerClick }: Props) {
  const [sectorFilter, setSectorFilter] = useState("all");
  const [signalFilter, setSignalFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("orchestratorScore");
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let list = predictions.predictions;
    if (sectorFilter !== "all") list = list.filter((p) => p.sector === sectorFilter);
    if (signalFilter !== "all") list = list.filter((p) => p.signalLabel === signalFilter);
    if (search) {
      const q = search.toUpperCase();
      list = list.filter((p) => p.ticker.includes(q));
    }
    const sorted = [...list].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      if (typeof av === "string" && typeof bv === "string") return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return sorted;
  }, [predictions.predictions, sectorFilter, signalFilter, search, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (
      sortAsc ? (
        <ChevronUp size={12} className="inline ml-0.5" />
      ) : (
        <ChevronDown size={12} className="inline ml-0.5" />
      )
    ) : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Predictions</h1>
          <p className="text-sm text-[var(--text-dim)]">
            Generated {predictions.meta.date} · {filtered.length} predictions · {predictions.meta.totalTickers} tickers · Jan–Jun 2026
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-[var(--text-dim)]">
          <Filter size={14} />
          <span className="text-xs">Filters:</span>
        </div>
        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-[var(--text)]"
        >
          <option value="all">All Sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <select
          value={signalFilter}
          onChange={(e) => setSignalFilter(e.target.value)}
          className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-[var(--text)]"
        >
          <option value="all">All Signals</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="HOLD">HOLD</option>
        </select>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-dim)]" />
          <input
            type="text"
            placeholder="Search ticker..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-1.5 text-[var(--text)] w-40"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-dim)]">
                {(
                  [
                    ["ticker", "Ticker"],
                    ["sector", "Sector"],
                    ["entryDate", "Entry Date"],
                    ["signalLabel", "Signal"],
                  ] as [SortKey, string][]
                ).map(([k, label]) => (
                  <th
                    key={k}
                    onClick={() => toggleSort(k)}
                    className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none whitespace-nowrap"
                  >
                    {label}
                    <SortIcon k={k} />
                  </th>
                ))}
                <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider whitespace-nowrap">
                  Exit Date
                </th>
                <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider whitespace-nowrap">
                  Sentiment
                </th>
                <th
                  onClick={() => toggleSort("targetPrice")}
                  className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none whitespace-nowrap"
                >
                  Target Price
                  <SortIcon k={"targetPrice" as SortKey} />
                </th>
                <th
                  onClick={() => toggleSort("profitPct")}
                  className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none whitespace-nowrap"
                >
                  Profit %
                  <SortIcon k={"profitPct" as SortKey} />
                </th>
                <th
                  onClick={() => toggleSort("confidence")}
                  className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none whitespace-nowrap"
                >
                  Confidence
                  <SortIcon k={"confidence" as SortKey} />
                </th>
                <th
                  onClick={() => toggleSort("orchestratorScore")}
                  className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none whitespace-nowrap"
                >
                  Score
                  <SortIcon k={"orchestratorScore" as SortKey} />
                </th>
                <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider whitespace-nowrap">
                  Win Rate
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, idx) => {
                const rowKey = `${p.ticker}-${p.date}-${idx}`;
                const isExpanded = expandedTicker === rowKey;
                const profitColor =
                  (p.profitPct ?? 0) > 0
                    ? "text-green-400"
                    : (p.profitPct ?? 0) < 0
                    ? "text-red-400"
                    : "text-[var(--text-dim)]";
                return (
                  <>
                    <tr
                      key={rowKey}
                      onClick={() =>
                        setExpandedTicker(isExpanded ? null : rowKey)
                      }
                      className={`border-b border-[var(--border)]/50 cursor-pointer transition-colors ${
                        isExpanded
                          ? "bg-indigo-500/5"
                          : "hover:bg-white/3"
                      }`}
                    >
                      <td className="px-3 py-3 font-mono font-bold whitespace-nowrap">{p.ticker}</td>
                      <td className="px-3 py-3 text-xs text-[var(--text-dim)] whitespace-nowrap">
                        {p.sector.replace("_", " ")}
                      </td>
                      <td className="px-3 py-3 text-xs font-mono whitespace-nowrap">
                        {formatDate(p.entryDate)}
                      </td>
                      <td className="px-3 py-3">
                        <SignalBadge signal={p.signalLabel} />
                      </td>
                      <td className="px-3 py-3 text-xs font-mono whitespace-nowrap">
                        {formatDate(p.exitDate)}
                      </td>
                      <td className="px-3 py-3">
                        <SentimentBadge sentiment={p.sentiment} />
                      </td>
                      <td className="px-3 py-3 font-mono text-blue-400 whitespace-nowrap">
                        {p.targetPrice != null ? `$${p.targetPrice.toFixed(2)}` : "—"}
                      </td>
                      <td className={`px-3 py-3 font-mono font-semibold whitespace-nowrap ${profitColor}`}>
                        {p.profitPct != null ? `${p.profitPct > 0 ? "+" : ""}${p.profitPct.toFixed(2)}%` : "—"}
                      </td>
                      <td className="px-3 py-3">
                        <ConfidenceBar value={p.confidence} />
                      </td>
                      <td className="px-3 py-3 font-mono text-xs">
                        {p.orchestratorScore.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 font-mono text-xs whitespace-nowrap">
                        {p.winRatePct != null ? `${p.winRatePct.toFixed(0)}%` : "—"}
                      </td>
                    </tr>
                    {isExpanded && (
                      <ExpandedRow key={`${rowKey}-exp`} p={p} onTickerClick={onTickerClick} />
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
