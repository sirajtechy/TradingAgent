"use client";

import { useMemo, useState } from "react";
import type { Signal } from "../lib/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";

interface Props {
  signals: Signal[];
  sectors: string[];
  onTickerClick: (t: string) => void;
}

export default function MisclassificationView({ signals, sectors, onTickerClick }: Props) {
  const [agentFilter, setAgentFilter] = useState("all");
  const agents = [...new Set(signals.map((s) => s.agent))];

  const misclassified = useMemo(() => {
    let list = signals.filter((s) => s.correct === false);
    if (agentFilter !== "all") list = list.filter((s) => s.agent === agentFilter);
    return list;
  }, [signals, agentFilter]);

  const totalMisclass = misclassified.length;
  const fp = misclassified.filter((s) => s.signal === "BUY" && s.actualDirection === "down").length;
  const fn = misclassified.filter((s) => s.signal === "SELL" && s.actualDirection === "up").length;
  const avgLoss = misclassified.length > 0
    ? misclassified.reduce((sum, s) => sum + Math.abs(s.returnPct), 0) / misclassified.length
    : 0;

  // By sector
  const bySector = useMemo(() => {
    const map: Record<string, number> = {};
    misclassified.forEach((s) => {
      map[s.sector] = (map[s.sector] || 0) + 1;
    });
    return Object.entries(map)
      .map(([sector, count]) => ({ sector: sector.replace("_", " "), count }))
      .sort((a, b) => b.count - a.count);
  }, [misclassified]);

  // By month
  const byMonth = useMemo(() => {
    const map: Record<string, number> = {};
    misclassified.forEach((s) => {
      map[s.month] = (map[s.month] || 0) + 1;
    });
    return Object.entries(map)
      .sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime())
      .map(([month, count]) => ({
        month: new Date(month + " 1").toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
        count,
      }));
  }, [misclassified]);

  // Error type breakdown
  const errorTypes = [
    { name: "False Positive (BUY→DOWN)", value: fp, color: "#ef4444" },
    { name: "False Negative (SELL→UP)", value: fn, color: "#f97316" },
    { name: "Other Errors", value: totalMisclass - fp - fn, color: "#eab308" },
  ];

  // Top offending tickers
  const topOffenders = useMemo(() => {
    const map: Record<string, { count: number; totalLoss: number }> = {};
    misclassified.forEach((s) => {
      if (!map[s.ticker]) map[s.ticker] = { count: 0, totalLoss: 0 };
      map[s.ticker].count++;
      map[s.ticker].totalLoss += Math.abs(s.returnPct);
    });
    return Object.entries(map)
      .map(([ticker, d]) => ({ ticker, ...d, avgLoss: d.totalLoss / d.count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [misclassified]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Misclassification Analysis</h1>
          <p className="text-sm text-[var(--text-dim)]">{totalMisclass} errors found</p>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setAgentFilter("all")}
            className={`text-xs px-3 py-1.5 rounded-lg ${agentFilter === "all" ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30" : "text-[var(--text-dim)] hover:bg-white/5"}`}
          >
            All
          </button>
          {agents.map((a) => (
            <button
              key={a}
              onClick={() => setAgentFilter(a)}
              className={`text-xs px-3 py-1.5 rounded-lg capitalize ${agentFilter === a ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30" : "text-[var(--text-dim)] hover:bg-white/5"}`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-red-500/30 bg-gradient-to-br from-red-500/10 to-transparent p-4">
          <p className="text-xs text-[var(--text-dim)] uppercase">Total Errors</p>
          <p className="text-2xl font-bold text-red-400">{totalMisclass}</p>
        </div>
        <div className="rounded-xl border border-red-500/30 bg-gradient-to-br from-red-500/10 to-transparent p-4">
          <p className="text-xs text-[var(--text-dim)] uppercase">False Positives</p>
          <p className="text-2xl font-bold text-red-400">{fp}</p>
          <p className="text-xs text-[var(--text-dim)]">BUY → DOWN</p>
        </div>
        <div className="rounded-xl border border-orange-500/30 bg-gradient-to-br from-orange-500/10 to-transparent p-4">
          <p className="text-xs text-[var(--text-dim)] uppercase">False Negatives</p>
          <p className="text-2xl font-bold text-orange-400">{fn}</p>
          <p className="text-xs text-[var(--text-dim)]">SELL → UP</p>
        </div>
        <div className="rounded-xl border border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-transparent p-4">
          <p className="text-xs text-[var(--text-dim)] uppercase">Avg Loss</p>
          <p className="text-2xl font-bold text-yellow-400">{avgLoss.toFixed(1)}%</p>
        </div>
      </div>

      {/* Row: Error Type Pie + Sector Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            Error Type Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={errorTypes} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${value}`}>
                {errorTypes.map((e, i) => (
                  <Cell key={i} fill={e.color} />
                ))}
              </Pie>
              <Legend />
              <Tooltip contentStyle={{ background: "#1a1a24", border: "1px solid #2a2a3a", borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            Errors by Sector
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={bySector} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="sector" width={120} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#1a1a24", border: "1px solid #2a2a3a", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monthly Trend */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
        <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
          Monthly Error Trend
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={byMonth}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#1a1a24", border: "1px solid #2a2a3a", borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="count" fill="#f97316" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Offenders */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
        <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
          Top Offending Tickers
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-dim)]">
                <th className="px-3 py-2 text-left text-xs">#</th>
                <th className="px-3 py-2 text-left text-xs">Ticker</th>
                <th className="px-3 py-2 text-right text-xs">Errors</th>
                <th className="px-3 py-2 text-right text-xs">Avg Loss</th>
                <th className="px-3 py-2 text-right text-xs">Total Loss</th>
              </tr>
            </thead>
            <tbody>
              {topOffenders.map((t, i) => (
                <tr key={t.ticker} className="border-b border-[var(--border)]/30 hover:bg-white/3">
                  <td className="px-3 py-2 text-xs text-[var(--text-dim)]">{i + 1}</td>
                  <td className="px-3 py-2">
                    <button onClick={() => onTickerClick(t.ticker)} className="font-mono font-bold text-indigo-400 hover:underline">
                      {t.ticker}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-red-400">{t.count}</td>
                  <td className="px-3 py-2 text-right font-mono text-red-400">{t.avgLoss.toFixed(1)}%</td>
                  <td className="px-3 py-2 text-right font-mono text-red-400">{t.totalLoss.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
