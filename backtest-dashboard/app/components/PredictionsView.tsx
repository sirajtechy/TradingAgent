"use client";

import { useState, useMemo } from "react";
import { getPredictionData } from "@/app/lib/data";
import { Prediction } from "@/app/lib/types";
import StatCard from "./StatCard";
import BarChart from "./BarChart";

export default function PredictionsView() {
  const data = getPredictionData();
  const { summary, sectorSummaries, predictions, highConfidenceSetups } = data;

  const [sectorFilter, setSectorFilter] = useState("all");
  const [signalFilter, setSignalFilter] = useState("all");
  const [sortKey, setSortKey] = useState<string>("orchestratorScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [expanded, setExpanded] = useState<string | null>(null);

  const sectors = Object.keys(sectorSummaries).sort();

  const filtered = useMemo(() => {
    let p = predictions;
    if (sectorFilter !== "all") p = p.filter((x) => x.sector === sectorFilter);
    if (signalFilter !== "all") p = p.filter((x) => x.signal === signalFilter);
    return [...p].sort((a, b) => {
      const av = (a as unknown as Record<string, unknown>)[sortKey];
      const bv = (b as unknown as Record<string, unknown>)[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [predictions, sectorFilter, signalFilter, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const SortIcon = ({ col }: { col: string }) => {
    if (sortKey !== col) return <span className="text-gray-700 ml-1">↕</span>;
    return <span className="text-blue-400 ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  const signalBadge = (sig: string) => {
    const map: Record<string, string> = {
      bullish: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      bearish: "bg-red-500/20 text-red-400 border-red-500/30",
      neutral: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    };
    return (
      <span className={`px-2 py-0.5 rounded border text-xs font-bold uppercase ${map[sig] || ""}`}>
        {sig}
      </span>
    );
  };

  const scorePill = (score: number | null, label?: string) => {
    if (score == null) return <span className="text-gray-600">—</span>;
    let color = "text-gray-400";
    if (score >= 62) color = "text-emerald-400";
    else if (score < 38) color = "text-red-400";
    else color = "text-amber-400";
    return (
      <span className={`font-mono text-xs ${color}`}>
        {label ? `${label} ` : ""}{score.toFixed(1)}
      </span>
    );
  };

  const confBar = (conf: number) => {
    const w = Math.min(conf * 100, 100);
    const color = conf >= 0.4 ? "bg-emerald-500" : conf >= 0.2 ? "bg-amber-500" : "bg-gray-600";
    return (
      <div className="flex items-center gap-2">
        <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
        </div>
        <span className="text-xs font-mono text-gray-400">{(conf * 100).toFixed(0)}%</span>
      </div>
    );
  };

  // Sector bar chart
  const sectorScores = useMemo(() => {
    const colors: Record<string, string> = {
      Technology: "#3b82f6",
      Healthcare: "#ef4444",
      Financials: "#f59e0b",
      Consumer_Staples: "#10b981",
      Energy: "#8b5cf6",
    };
    return sectors.map((sec) => ({
      label: sec,
      value: sectorSummaries[sec].avgScore,
      color: colors[sec] || "#6b7280",
    }));
  }, [sectors, sectorSummaries]);

  // Signal distribution for bar chart
  const signalDist = useMemo(() => {
    return [
      { label: "Bullish", value: summary.bullish, color: "#10b981" },
      { label: "Bearish", value: summary.bearish, color: "#ef4444" },
      { label: "Neutral", value: summary.neutral, color: "#6b7280" },
    ];
  }, [summary]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-100">Live Predictions</h2>
          <p className="text-xs text-gray-500">{data.meta.date} · {data.meta.agents}</p>
        </div>
        {highConfidenceSetups.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Top picks:</span>
            {highConfidenceSetups.slice(0, 5).map((t) => (
              <span key={t} className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard label="Total Tickers" value={data.meta.totalTickers} color="blue" />
        <StatCard label="Bullish" value={summary.bullish} color="emerald" />
        <StatCard label="Bearish" value={summary.bearish} color="red" />
        <StatCard label="Neutral" value={summary.neutral} color="gray" />
        <StatCard label="Avg Score" value={summary.avgScore} color={summary.avgScore >= 55 ? "emerald" : summary.avgScore >= 45 ? "amber" : "red"} />
        <StatCard label="Agreement" value={`${summary.agreementRate}%`} color={summary.agreementRate >= 80 ? "emerald" : "amber"} />
        <StatCard label="Conflicts" value={summary.conflictCount} color={summary.conflictCount === 0 ? "emerald" : "amber"} />
      </div>

      {/* Sector heatmap + charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sector heatmap grid */}
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Sector Sentiment</h3>
          <div className="grid grid-cols-1 gap-3">
            {sectors.map((sec) => {
              const s = sectorSummaries[sec];
              const total = s.bullish + s.bearish + s.neutral;
              const dominant = s.dominant;
              const bg = dominant === "bullish" ? "bg-emerald-500/10 border-emerald-500/20" : dominant === "bearish" ? "bg-red-500/10 border-red-500/20" : "bg-gray-800/50 border-gray-700";
              return (
                <div key={sec} className={`${bg} border rounded-lg p-3 flex items-center justify-between`}>
                  <div>
                    <span className="text-sm font-medium text-gray-200">{sec.replace("_", " ")}</span>
                    <div className="flex gap-3 mt-1">
                      <span className="text-xs text-emerald-400">↑{s.bullish}</span>
                      <span className="text-xs text-red-400">↓{s.bearish}</span>
                      <span className="text-xs text-gray-500">—{s.neutral}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-lg font-bold ${dominant === "bullish" ? "text-emerald-400" : dominant === "bearish" ? "text-red-400" : "text-gray-400"}`}>
                      {s.avgScore.toFixed(0)}
                    </span>
                    <p className="text-[10px] text-gray-500">avg score</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-4">
          <BarChart data={sectorScores} title="Avg Score by Sector" />
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Signal Distribution</h3>
            <div className="flex items-end gap-4 justify-center h-32">
              {signalDist.map((d) => {
                const maxH = Math.max(...signalDist.map((x) => x.value), 1);
                const h = (d.value / maxH) * 100;
                return (
                  <div key={d.label} className="flex flex-col items-center gap-1">
                    <span className="text-xs font-bold text-gray-300">{d.value}</span>
                    <div
                      className="w-14 rounded-t-md transition-all duration-500"
                      style={{ height: `${h}%`, backgroundColor: d.color }}
                    />
                    <span className="text-[10px] text-gray-500">{d.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Sectors</option>
          {sectors.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
        <select
          value={signalFilter}
          onChange={(e) => setSignalFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Signals</option>
          <option value="bullish">Bullish</option>
          <option value="bearish">Bearish</option>
          <option value="neutral">Neutral</option>
        </select>
        <span className="text-xs text-gray-500">{filtered.length} results</span>
      </div>

      {/* Prediction table */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-800/50">
              <tr>
                {[
                  { key: "ticker", label: "Ticker" },
                  { key: "sector", label: "Sector" },
                  { key: "signal", label: "Signal" },
                  { key: "orchestratorScore", label: "Score" },
                  { key: "confidence", label: "Confidence" },
                  { key: "techSignal", label: "Tech" },
                  { key: "techScore", label: "Tech Score" },
                  { key: "fundSignal", label: "Fund" },
                  { key: "fundScore", label: "Fund Score" },
                  { key: "conflictDetected", label: "Conflict" },
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
              {filtered.map((p) => {
                const isExpanded = expanded === p.ticker;
                const isHighConf = highConfidenceSetups.includes(p.ticker);
                return (
                  <>
                    <tr
                      key={p.ticker}
                      className={`border-t border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors ${
                        isHighConf ? "bg-emerald-500/5" : ""
                      }`}
                      onClick={() => setExpanded(isExpanded ? null : p.ticker)}
                    >
                      <td className="py-2.5 px-3 font-bold text-gray-100">
                        {isHighConf && <span className="text-amber-400 mr-1">★</span>}
                        {p.ticker}
                      </td>
                      <td className="py-2.5 px-3 text-gray-400">{p.sector.replace("_", " ")}</td>
                      <td className="py-2.5 px-3">{signalBadge(p.signal)}</td>
                      <td className="py-2.5 px-3">{scorePill(p.orchestratorScore)}</td>
                      <td className="py-2.5 px-3">{confBar(p.confidence)}</td>
                      <td className="py-2.5 px-3">{signalBadge(p.techSignal || "—")}</td>
                      <td className="py-2.5 px-3">{scorePill(p.techScore)}</td>
                      <td className="py-2.5 px-3">{signalBadge(p.fundSignal || "—")}</td>
                      <td className="py-2.5 px-3">{scorePill(p.fundScore)}</td>
                      <td className="py-2.5 px-3">
                        {p.conflictDetected ? (
                          <span className="text-amber-400">⚡</span>
                        ) : (
                          <span className="text-emerald-500">✓</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${p.ticker}-detail`} className="border-t border-gray-800/30">
                        <td colSpan={10} className="p-4 bg-gray-900/80">
                          <ExpandedDetail prediction={p} />
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

      {/* Conflict analysis */}
      {(() => {
        const conflicts = predictions.filter((p) => p.conflictDetected);
        if (conflicts.length === 0) return null;
        return (
          <div className="bg-gray-900/50 border border-amber-800/30 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-amber-400 mb-3">⚡ Conflict Analysis ({conflicts.length})</h3>
            <div className="space-y-2">
              {conflicts.map((p) => (
                <div key={p.ticker} className="flex items-center gap-4 text-xs">
                  <span className="font-bold text-gray-200 w-12">{p.ticker}</span>
                  <span className="text-gray-500">{p.sector.replace("_", " ")}</span>
                  <span className="text-blue-400">Tech: {p.techSignal}</span>
                  <span className="text-gray-600">vs</span>
                  <span className="text-emerald-400">Fund: {p.fundSignal}</span>
                  <span className="text-gray-600">→</span>
                  {signalBadge(p.signal)}
                  {p.conflictResolution && (
                    <span className="text-gray-500 truncate max-w-xs">{p.conflictResolution}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ─── Expanded Detail Panel ───────────────────────────────────────────

function ExpandedDetail({ prediction: p }: { prediction: Prediction }) {
  const techFrameworks = [
    "ema_trend", "macd_system", "rsi_regime", "bollinger",
    "volume_obv", "adx_stochastic", "pattern_recognition", "ichimoku", "momentum",
  ];
  const fundFrameworks = ["financial_health", "valuation", "quality", "growth"];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Technical breakdown */}
      <div>
        <h4 className="text-xs font-semibold text-blue-400 mb-2 uppercase tracking-wider">Technical Agent</h4>
        {p.techScore != null ? (
          <>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-lg font-bold ${p.techScore >= 60 ? "text-emerald-400" : p.techScore < 35 ? "text-red-400" : "text-amber-400"}`}>
                {p.techScore.toFixed(1)}
              </span>
              <span className="text-xs text-gray-500 px-2 py-0.5 rounded bg-gray-800">{p.techBand}</span>
            </div>
            <div className="space-y-1.5">
              {techFrameworks.map((fw) => {
                const val = p.techSubscores[fw];
                if (val == null) return null;
                const w = Math.min(val, 100);
                const color = val >= 70 ? "bg-emerald-500" : val >= 50 ? "bg-amber-500" : "bg-red-500";
                return (
                  <div key={fw} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 w-32 truncate">{fw.replace("_", " ")}</span>
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-gray-400 w-8 text-right">{val.toFixed(0)}</span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <p className="text-xs text-gray-600">No technical data available</p>
        )}
      </div>

      {/* Fundamental breakdown */}
      <div>
        <h4 className="text-xs font-semibold text-emerald-400 mb-2 uppercase tracking-wider">Fundamental Agent</h4>
        {p.fundScore != null ? (
          <>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-lg font-bold ${p.fundScore >= 62 ? "text-emerald-400" : p.fundScore < 40 ? "text-red-400" : "text-amber-400"}`}>
                {p.fundScore.toFixed(1)}
              </span>
              <span className="text-xs text-gray-500 px-2 py-0.5 rounded bg-gray-800">{p.fundBand}</span>
              {p.fundDataQuality && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  p.fundDataQuality === "good" ? "bg-emerald-500/10 text-emerald-500" :
                  p.fundDataQuality === "fair" ? "bg-amber-500/10 text-amber-500" :
                  "bg-red-500/10 text-red-500"
                }`}>
                  {p.fundDataQuality}
                </span>
              )}
            </div>
            <div className="space-y-1.5">
              {fundFrameworks.map((fw) => {
                const val = p.fundSubscores[fw];
                if (val == null) return null;
                const w = Math.min(val, 100);
                const color = val >= 60 ? "bg-emerald-500" : val >= 40 ? "bg-amber-500" : "bg-red-500";
                return (
                  <div key={fw} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 w-32 truncate">{fw.replace("_", " ")}</span>
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-gray-400 w-8 text-right">{val.toFixed(0)}</span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <p className="text-xs text-gray-600">No fundamental data available</p>
        )}
      </div>

      {/* Notes */}
      {(p.conflictResolution || p.note) && (
        <div className="md:col-span-2 border-t border-gray-800 pt-3">
          {p.conflictResolution && (
            <p className="text-xs text-amber-400">⚡ {p.conflictResolution}</p>
          )}
          {p.note && (
            <p className="text-xs text-gray-500 mt-1">{p.note}</p>
          )}
        </div>
      )}
    </div>
  );
}
