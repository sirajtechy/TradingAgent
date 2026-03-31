"use client";

import { Signal } from "@/app/lib/types";
import { useState, useMemo } from "react";

interface Props {
  signals: Signal[];
}

export default function MisclassificationExplorer({ signals }: Props) {
  const misses = useMemo(
    () => signals.filter((s) => s.correct === false).sort((a, b) => a.signalDate.localeCompare(b.signalDate)),
    [signals]
  );

  const [expanded, setExpanded] = useState<string | null>(null);

  // Group by sector
  const bySector = useMemo(() => {
    const m: Record<string, Signal[]> = {};
    for (const s of misses) {
      (m[s.sector] ??= []).push(s);
    }
    return m;
  }, [misses]);

  // Group by ticker
  const byTicker = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of misses) m[s.ticker] = (m[s.ticker] || 0) + 1;
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [misses]);

  // Group by month
  const byMonth = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of misses) m[s.month] = (m[s.month] || 0) + 1;
    return m;
  }, [misses]);

  const trades = signals.filter((s) => s.signal !== "HOLD");
  const missRate = trades.length ? ((misses.length / trades.length) * 100).toFixed(1) : "0";
  const fpCount = misses.filter((s) => s.signal === "BUY").length;
  const fnCount = misses.filter((s) => s.signal === "SELL").length;

  if (misses.length === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
        No misclassifications in current selection
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-400">Total Misclassifications</p>
          <p className="text-2xl font-bold text-red-400">{misses.length}</p>
          <p className="text-xs text-gray-500">{missRate}% of {trades.length} trades</p>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-400">False Positives (BUY→DOWN)</p>
          <p className="text-2xl font-bold text-amber-400">{fpCount}</p>
        </div>
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-400">False Negatives (SELL→UP)</p>
          <p className="text-2xl font-bold text-purple-400">{fnCount}</p>
        </div>
        <div className="bg-gray-500/10 border border-gray-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-400">Avg Loss on Misclass</p>
          <p className="text-2xl font-bold text-gray-300">
            {(misses.reduce((a, s) => a + Math.abs(s.returnPct), 0) / misses.length).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Sector heatmap */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Misclassifications by Sector</h3>
        <div className="grid grid-cols-5 gap-2">
          {Object.entries(bySector).map(([sector, sigs]) => {
            const fp = sigs.filter((s) => s.signal === "BUY").length;
            const fn = sigs.filter((s) => s.signal === "SELL").length;
            const intensity = Math.min(sigs.length / Math.max(...Object.values(bySector).map((s) => s.length)), 1);
            return (
              <div
                key={sector}
                className="rounded-lg p-3 text-center border border-gray-700/50"
                style={{ backgroundColor: `rgba(239, 68, 68, ${intensity * 0.3})` }}
              >
                <p className="text-xs font-medium text-gray-300">{sector.replace("_", " ")}</p>
                <p className="text-lg font-bold text-red-400">{sigs.length}</p>
                <p className="text-xs text-gray-500">FP:{fp} FN:{fn}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Monthly trend */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Monthly Trend</h3>
        <div className="flex items-end gap-1 h-32">
          {Object.entries(byMonth).map(([month, count]) => {
            const maxCount = Math.max(...Object.values(byMonth));
            const height = (count / maxCount) * 100;
            return (
              <div key={month} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-xs font-mono text-gray-400">{count}</span>
                <div
                  className="w-full bg-red-500/40 rounded-t border border-red-500/30"
                  style={{ height: `${height}%` }}
                />
                <span className="text-[10px] text-gray-600 whitespace-nowrap rotate-[-45deg] origin-top-left translate-y-2">
                  {month.replace(/\s\d{4}/, "")}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top offenders */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Top Misclassified Tickers</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {byTicker.slice(0, 10).map(([ticker, count]) => (
            <div
              key={ticker}
              className="flex items-center justify-between px-3 py-2 bg-gray-800/50 rounded-lg border border-gray-700/50"
            >
              <span className="font-mono font-bold text-sm text-gray-200">{ticker}</span>
              <span className="text-xs font-mono text-red-400 bg-red-500/10 px-2 py-0.5 rounded">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Detail table */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-300">Detailed Misclassification Log</h3>
        </div>
        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-xs">
            <thead className="bg-gray-800/50 sticky top-0">
              <tr>
                <th className="text-left py-2 px-3 text-gray-400">#</th>
                <th className="text-left py-2 px-3 text-gray-400">Agent</th>
                <th className="text-left py-2 px-3 text-gray-400">Ticker</th>
                <th className="text-left py-2 px-3 text-gray-400">Sector</th>
                <th className="text-left py-2 px-3 text-gray-400">Month</th>
                <th className="text-left py-2 px-3 text-gray-400">Predicted</th>
                <th className="text-left py-2 px-3 text-gray-400">Actual</th>
                <th className="text-left py-2 px-3 text-gray-400">Return</th>
                <th className="text-left py-2 px-3 text-gray-400">Score</th>
                <th className="text-left py-2 px-3 text-gray-400">Details</th>
              </tr>
            </thead>
            <tbody>
              {misses.map((s, i) => {
                const key = `${s.agent}-${s.ticker}-${s.signalDate}`;
                const isExpanded = expanded === key;
                return (
                  <>
                    <tr
                      key={key}
                      className="border-t border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                      onClick={() => setExpanded(isExpanded ? null : key)}
                    >
                      <td className="py-2 px-3 text-gray-500">{i + 1}</td>
                      <td className="py-2 px-3">
                        <span className={`text-xs font-medium ${
                          s.agent === "technical" ? "text-blue-400" :
                          s.agent === "fundamental" ? "text-emerald-400" : "text-purple-400"
                        }`}>{s.agent.slice(0, 4).toUpperCase()}</span>
                      </td>
                      <td className="py-2 px-3 font-mono font-bold text-gray-200">{s.ticker}</td>
                      <td className="py-2 px-3 text-gray-400">{s.sector.replace("_", " ")}</td>
                      <td className="py-2 px-3 text-gray-400">{s.month}</td>
                      <td className="py-2 px-3">
                        <span className={s.signal === "BUY" ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>
                          {s.signal}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className={s.actualDirection === "up" ? "text-emerald-400" : "text-red-400"}>
                          {s.actualDirection.toUpperCase()}
                        </span>
                      </td>
                      <td className={`py-2 px-3 font-mono ${s.returnPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {s.returnPct >= 0 ? "+" : ""}{s.returnPct.toFixed(1)}%
                      </td>
                      <td className="py-2 px-3 font-mono text-gray-300">{s.score?.toFixed(1) ?? "—"}</td>
                      <td className="py-2 px-3 text-gray-500">{isExpanded ? "▼" : "▶"}</td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${key}-detail`} className="bg-gray-800/20">
                        <td colSpan={10} className="p-4">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            <div>
                              <span className="text-gray-500">Score Band:</span>{" "}
                              <span className="text-gray-300">{s.scoreBand || "—"}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Start Price:</span>{" "}
                              <span className="font-mono text-gray-300">${s.startPrice.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">End Price:</span>{" "}
                              <span className="font-mono text-gray-300">${s.endPrice.toFixed(2)}</span>
                            </div>
                            {s.confidence !== undefined && (
                              <div>
                                <span className="text-gray-500">Confidence:</span>{" "}
                                <span className="font-mono text-gray-300">{(s.confidence * 100).toFixed(1)}%</span>
                              </div>
                            )}
                            {s.conflictDetected && (
                              <div>
                                <span className="text-gray-500">Conflict:</span>{" "}
                                <span className="text-amber-400">{s.conflictResolution || "Yes"}</span>
                              </div>
                            )}
                            {s.techScore !== undefined && (
                              <div>
                                <span className="text-gray-500">Tech Score:</span>{" "}
                                <span className="font-mono text-blue-400">{s.techScore?.toFixed(1)}</span>
                              </div>
                            )}
                            {s.fundScore !== undefined && (
                              <div>
                                <span className="text-gray-500">Fund Score:</span>{" "}
                                <span className="font-mono text-emerald-400">{s.fundScore?.toFixed(1)}</span>
                              </div>
                            )}
                          </div>
                          {s.frameworks && Object.keys(s.frameworks).length > 0 && (
                            <div className="mt-3">
                              <span className="text-gray-500 text-xs">Frameworks:</span>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {Object.entries(s.frameworks).map(([name, score]) => (
                                  <span
                                    key={name}
                                    className="px-2 py-1 bg-gray-800 rounded text-xs font-mono"
                                  >
                                    <span className="text-gray-400">{name}:</span>{" "}
                                    <span className={
                                      score != null && score >= 60 ? "text-emerald-400" :
                                      score != null && score <= 40 ? "text-red-400" : "text-gray-300"
                                    }>
                                      {score?.toFixed(0) ?? "—"}
                                    </span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
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
