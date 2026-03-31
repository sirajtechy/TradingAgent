"use client";

import { Signal } from "@/app/lib/types";
import { useState } from "react";

interface Props {
  signals: Signal[];
}

export default function SignalTable({ signals }: Props) {
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<string>("signalDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const pageSize = 25;

  const sorted = [...signals].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortKey];
    const bv = (b as unknown as Record<string, unknown>)[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const totalPages = Math.ceil(sorted.length / pageSize);
  const pageData = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
    setPage(0);
  };

  const SortIcon = ({ col }: { col: string }) => {
    if (sortKey !== col) return <span className="text-gray-700 ml-1">↕</span>;
    return <span className="text-blue-400 ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  const agentBadge = (agent: string) => {
    const colors: Record<string, string> = {
      technical: "bg-blue-500/20 text-blue-400",
      fundamental: "bg-emerald-500/20 text-emerald-400",
      orchestrator: "bg-purple-500/20 text-purple-400",
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[agent] || "bg-gray-700 text-gray-400"}`}>
        {agent.slice(0, 4).toUpperCase()}
      </span>
    );
  };

  const signalBadge = (sig: string) => {
    const colors: Record<string, string> = {
      BUY: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      SELL: "bg-red-500/20 text-red-400 border-red-500/30",
      HOLD: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    };
    return (
      <span className={`px-2 py-0.5 rounded border text-xs font-bold ${colors[sig] || ""}`}>
        {sig}
      </span>
    );
  };

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">
          Signal Log <span className="text-gray-500 font-normal">({signals.length} signals)</span>
        </h3>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-30"
          >
            ← Prev
          </button>
          <span>
            {page + 1} / {totalPages || 1}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-800/50">
            <tr>
              {[
                { key: "agent", label: "Agent" },
                { key: "ticker", label: "Ticker" },
                { key: "sector", label: "Sector" },
                { key: "month", label: "Month" },
                { key: "signal", label: "Signal" },
                { key: "score", label: "Score" },
                { key: "actualDirection", label: "Actual" },
                { key: "returnPct", label: "Return" },
                { key: "correct", label: "Result" },
              ].map(({ key, label }) => (
                <th
                  key={key}
                  className="text-left py-3 px-3 font-medium text-gray-400 cursor-pointer hover:text-gray-200 select-none whitespace-nowrap"
                  onClick={() => toggleSort(key)}
                >
                  {label}
                  <SortIcon col={key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((s, i) => (
              <tr
                key={`${s.agent}-${s.ticker}-${s.signalDate}-${i}`}
                className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors"
              >
                <td className="py-2 px-3">{agentBadge(s.agent)}</td>
                <td className="py-2 px-3 font-mono font-bold text-gray-200">{s.ticker}</td>
                <td className="py-2 px-3 text-gray-400">{s.sector.replace("_", " ")}</td>
                <td className="py-2 px-3 text-gray-400 whitespace-nowrap">{s.month}</td>
                <td className="py-2 px-3">{signalBadge(s.signal)}</td>
                <td className="py-2 px-3 font-mono text-gray-300">
                  {s.score != null ? s.score.toFixed(1) : "—"}
                </td>
                <td className="py-2 px-3">
                  <span className={s.actualDirection === "up" ? "text-emerald-400" : "text-red-400"}>
                    {s.actualDirection === "up" ? "▲ UP" : "▼ DOWN"}
                  </span>
                </td>
                <td className={`py-2 px-3 font-mono font-bold ${s.returnPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {s.returnPct >= 0 ? "+" : ""}{s.returnPct.toFixed(1)}%
                </td>
                <td className="py-2 px-3 text-center">
                  {s.correct === true ? "✅" : s.correct === false ? "❌" : "➖"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
