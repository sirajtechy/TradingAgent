"use client";

import { useMemo, useState } from "react";
import type { Signal, AgentName, SignalLabel } from "../lib/types";
import { ChevronDown, ChevronUp, Download, Filter, Search } from "lucide-react";

interface Props {
  signals: Signal[];
  sectors: string[];
  tickers: string[];
  months: string[];
  onTickerClick: (t: string) => void;
}

type SortKey = "ticker" | "month" | "agent" | "signal" | "returnPct" | "score" | "startPrice" | "endPrice";

const PAGE_SIZE = 25;

export default function SignalExplorer({ signals, sectors, tickers, months, onTickerClick }: Props) {
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [signalFilter, setSignalFilter] = useState("all");
  const [correctFilter, setCorrectFilter] = useState("all");
  const [monthFilter, setMonthFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("month");
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    let list = signals;
    if (agentFilter !== "all") list = list.filter((s) => s.agent === agentFilter);
    if (sectorFilter !== "all") list = list.filter((s) => s.sector === sectorFilter);
    if (signalFilter !== "all") list = list.filter((s) => s.signal === signalFilter);
    if (correctFilter === "correct") list = list.filter((s) => s.correct === true);
    else if (correctFilter === "incorrect") list = list.filter((s) => s.correct === false);
    else if (correctFilter === "abstained") list = list.filter((s) => s.correct === null);
    if (monthFilter !== "all") list = list.filter((s) => s.month === monthFilter);
    if (search) {
      const q = search.toUpperCase();
      list = list.filter((s) => s.ticker.includes(q));
    }
    const sorted = [...list].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      if (typeof av === "string" && typeof bv === "string")
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return sorted;
  }, [signals, agentFilter, sectorFilter, signalFilter, correctFilter, monthFilter, search, sortKey, sortAsc]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (
      sortAsc ? <ChevronUp size={10} className="inline" /> : <ChevronDown size={10} className="inline" />
    ) : null;

  // CSV export
  const exportCSV = () => {
    const header = "Ticker,Sector,Agent,Month,Signal,EntryPrice,ExitPrice,Return%,Score,Band,Correct\n";
    const rows = filtered
      .map(
        (s) =>
          `${s.ticker},${s.sector},${s.agent},${s.month},${s.signal},${s.startPrice},${s.endPrice},${s.returnPct},${s.score ?? ""},${s.scoreBand ?? ""},${s.correct ?? ""}`
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "signals.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const agents = [...new Set(signals.map((s) => s.agent))];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signal Explorer</h1>
          <p className="text-sm text-[var(--text-dim)]">
            {filtered.length} of {signals.length} signals
          </p>
        </div>
        <button
          onClick={exportCSV}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
        >
          <Download size={14} /> Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2.5">
        <Filter size={14} className="text-[var(--text-dim)]" />
        {/* Agent toggles */}
        <div className="flex gap-1">
          <button
            onClick={() => setAgentFilter("all")}
            className={`text-xs px-2.5 py-1 rounded-lg ${
              agentFilter === "all"
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                : "text-[var(--text-dim)] hover:bg-white/5"
            }`}
          >
            All
          </button>
          {agents.map((a) => (
            <button
              key={a}
              onClick={() => setAgentFilter(a)}
              className={`text-xs px-2.5 py-1 rounded-lg capitalize ${
                agentFilter === a
                  ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                  : "text-[var(--text-dim)] hover:bg-white/5"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
        <select value={sectorFilter} onChange={(e) => { setSectorFilter(e.target.value); setPage(0); }} className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-[var(--text)]">
          <option value="all">All Sectors</option>
          {sectors.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
        <select value={signalFilter} onChange={(e) => { setSignalFilter(e.target.value); setPage(0); }} className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-[var(--text)]">
          <option value="all">All Signals</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="HOLD">HOLD</option>
        </select>
        <select value={correctFilter} onChange={(e) => { setCorrectFilter(e.target.value); setPage(0); }} className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-[var(--text)]">
          <option value="all">All Results</option>
          <option value="correct">Correct</option>
          <option value="incorrect">Incorrect</option>
          <option value="abstained">Abstained</option>
        </select>
        <select value={monthFilter} onChange={(e) => { setMonthFilter(e.target.value); setPage(0); }} className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-[var(--text)]">
          <option value="all">All Months</option>
          {months.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-dim)]" />
          <input type="text" placeholder="Ticker..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} className="text-xs bg-[var(--bg-card)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-1.5 text-[var(--text)] w-32" />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-dim)]">
                {([
                  ["ticker", "Ticker"],
                  ["agent", "Agent"],
                  ["month", "Month"],
                  ["signal", "Signal"],
                  ["startPrice", "Entry"],
                  ["endPrice", "Exit"],
                  ["returnPct", "Return"],
                  ["score", "Score"],
                ] as [SortKey, string][]).map(([k, label]) => (
                  <th
                    key={k}
                    onClick={() => toggleSort(k)}
                    className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-[var(--text)] select-none"
                  >
                    {label} <SortIcon k={k} />
                  </th>
                ))}
                <th className="px-3 py-2.5 text-xs font-medium uppercase tracking-wider text-center">Result</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((s, i) => (
                <tr
                  key={`${s.ticker}-${s.agent}-${s.month}-${i}`}
                  className="border-b border-[var(--border)]/30 hover:bg-white/3"
                >
                  <td className="px-3 py-2">
                    <button onClick={() => onTickerClick(s.ticker)} className="font-mono font-bold text-indigo-400 hover:underline">
                      {s.ticker}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded capitalize ${
                      s.agent === "technical" ? "bg-indigo-500/20 text-indigo-400" :
                      s.agent === "fundamental" ? "bg-green-500/20 text-green-400" :
                      "bg-purple-500/20 text-purple-400"
                    }`}>
                      {s.agent}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--text-dim)]">{s.month}</td>
                  <td className="px-3 py-2">
                    <span className={`text-xs font-semibold ${
                      s.signal === "BUY" ? "text-green-400" :
                      s.signal === "SELL" ? "text-red-400" : "text-yellow-400"
                    }`}>
                      {s.signal}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">${s.startPrice.toFixed(2)}</td>
                  <td className="px-3 py-2 font-mono text-xs">${s.endPrice.toFixed(2)}</td>
                  <td className={`px-3 py-2 font-mono text-xs font-medium ${s.returnPct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {s.returnPct >= 0 ? "+" : ""}{s.returnPct.toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{s.score !== null ? s.score.toFixed(0) : "—"}</td>
                  <td className="px-3 py-2 text-center">
                    {s.correct === null ? <span className="text-xs text-[var(--text-dim)]">—</span> :
                     s.correct ? <span className="text-xs text-green-400">✓</span> : <span className="text-xs text-red-400">✗</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border)]">
          <span className="text-xs text-[var(--text-dim)]">
            Page {page + 1} of {totalPages} · {filtered.length} signals
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="text-xs px-3 py-1 rounded bg-white/5 disabled:opacity-30 hover:bg-white/10"
            >
              Prev
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="text-xs px-3 py-1 rounded bg-white/5 disabled:opacity-30 hover:bg-white/10"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
