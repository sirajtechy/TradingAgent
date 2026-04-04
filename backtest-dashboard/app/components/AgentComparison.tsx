"use client";

import { useMemo } from "react";
import type { AgentSummary, Signal } from "../lib/types";
import { winRate, sharpeRatio, maxDrawdown, profitFactor } from "../lib/data-utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
} from "recharts";

interface Props {
  summaries: AgentSummary[];
  signals: Signal[];
  months: string[];
}

const AGENT_COLORS: Record<string, string> = {
  technical: "#6366f1",
  fundamental: "#22c55e",
  orchestrator: "#a855f7",
};

function ConfusionGrid({ cm }: { cm: { buyUp: number; buyDown: number; sellUp: number; sellDown: number; holdUp: number; holdDown: number } }) {
  const cells = [
    { label: "BUY→UP", val: cm.buyUp, good: true },
    { label: "BUY→DOWN", val: cm.buyDown, good: false },
    { label: "SELL→UP", val: cm.sellUp, good: false },
    { label: "SELL→DOWN", val: cm.sellDown, good: true },
    { label: "HOLD→UP", val: cm.holdUp, good: false },
    { label: "HOLD→DOWN", val: cm.holdDown, good: false },
  ];
  const maxVal = Math.max(...cells.map((c) => c.val), 1);
  return (
    <div className="grid grid-cols-2 gap-1">
      {cells.map((c) => (
        <div
          key={c.label}
          className={`p-2 rounded text-center text-xs ${
            c.good
              ? "bg-green-500/10 border border-green-500/20"
              : "bg-red-500/10 border border-red-500/20"
          }`}
          style={{ opacity: 0.4 + (c.val / maxVal) * 0.6 }}
        >
          <div className="text-[10px] text-[var(--text-dim)]">{c.label}</div>
          <div className="font-bold font-mono">{c.val}</div>
        </div>
      ))}
    </div>
  );
}

export default function AgentComparison({ summaries, signals, months }: Props) {
  // Monthly win rate per agent
  const monthlyWR = useMemo(() => {
    return months.map((m) => {
      const row: Record<string, unknown> = {
        month: new Date(m + " 1").toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      };
      for (const s of summaries) {
        const agentSignals = signals.filter((sig) => sig.agent === s.agent && sig.month === m);
        row[s.agent] = Math.round(winRate(agentSignals) * 10) / 10;
      }
      return row;
    });
  }, [summaries, signals, months]);

  // Per-sector comparison
  const sectorComparison = useMemo(() => {
    const sectors = [...new Set(signals.map((s) => s.sector))].sort();
    return sectors.map((sec) => {
      const row: Record<string, unknown> = { sector: sec.replace("_", " ") };
      for (const s of summaries) {
        const bySec = s.bySector[sec];
        row[s.agent] = bySec ? (bySec.winRate ?? 0) : 0;
      }
      return row;
    });
  }, [summaries, signals]);

  // Agent stats table data
  const agentStats = summaries.map((s) => {
    const agentSignals = signals.filter((sig) => sig.agent === s.agent);
    return {
      agent: s.agent,
      winRate: (s.winRate ?? 0).toFixed(1),
      trades: s.totalTrades,
      periods: s.totalPeriods,
      buys: s.buys,
      sells: s.sells,
      holds: s.holds,
      sharpe: sharpeRatio(agentSignals).toFixed(2),
      maxDD: maxDrawdown(agentSignals).toFixed(1),
      pf: profitFactor(agentSignals),
      tickers: s.tickers.length,
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Comparison</h1>
        <p className="text-sm text-[var(--text-dim)]">
          Side-by-side performance of {summaries.length} agents
        </p>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agentStats.map((a) => (
          <div
            key={a.agent}
            className="rounded-xl border bg-[var(--bg-card)] p-5"
            style={{ borderColor: (AGENT_COLORS[a.agent] || "#6366f1") + "40" }}
          >
            <div className="flex items-center gap-2 mb-4">
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: AGENT_COLORS[a.agent] }}
              />
              <h3 className="text-sm font-semibold capitalize">{a.agent}</h3>
            </div>

            {/* Win Rate bar */}
            <div className="mb-4">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[var(--text-dim)]">Win Rate</span>
                <span className="font-mono font-bold">{a.winRate}%</span>
              </div>
              <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${a.winRate}%`,
                    background: AGENT_COLORS[a.agent],
                  }}
                />
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-3 text-xs mb-4">
              <div>
                <span className="text-[var(--text-dim)]">Trades</span>
                <p className="font-mono font-bold">{a.trades}</p>
              </div>
              <div>
                <span className="text-[var(--text-dim)]">Tickers</span>
                <p className="font-mono font-bold">{a.tickers}</p>
              </div>
              <div>
                <span className="text-[var(--text-dim)]">Sharpe</span>
                <p className="font-mono font-bold">{a.sharpe}</p>
              </div>
              <div>
                <span className="text-[var(--text-dim)]">Max DD</span>
                <p className="font-mono font-bold text-red-400">{a.maxDD}%</p>
              </div>
              <div>
                <span className="text-[var(--text-dim)]">Profit Factor</span>
                <p className="font-mono font-bold">
                  {a.pf === Infinity ? "∞" : a.pf.toFixed(2)}
                </p>
              </div>
              <div>
                <span className="text-[var(--text-dim)]">Holds</span>
                <p className="font-mono font-bold">{a.holds}</p>
              </div>
            </div>

            {/* Signal distribution */}
            <div className="flex h-5 rounded overflow-hidden text-[10px] font-medium">
              <div
                className="flex items-center justify-center bg-green-500/70"
                style={{ width: `${(a.buys / a.periods) * 100}%` }}
              >
                {a.buys}
              </div>
              <div
                className="flex items-center justify-center bg-red-500/70"
                style={{ width: `${(a.sells / a.periods) * 100}%` }}
              >
                {a.sells}
              </div>
              <div
                className="flex items-center justify-center bg-yellow-500/60"
                style={{ width: `${(a.holds / a.periods) * 100}%` }}
              >
                {a.holds}
              </div>
            </div>

            {/* Confusion Matrix */}
            <div className="mt-4">
              <p className="text-[10px] text-[var(--text-dim)] uppercase mb-2">Confusion Matrix</p>
              <ConfusionGrid
                cm={
                  summaries.find((s) => s.agent === a.agent)?.cm || {
                    buyUp: 0,
                    buyDown: 0,
                    sellUp: 0,
                    sellDown: 0,
                    holdUp: 0,
                    holdDown: 0,
                  }
                }
              />
            </div>
          </div>
        ))}
      </div>

      {/* Monthly Win Rate Trend */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
        <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
          Monthly Win Rate Trend
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={monthlyWR}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#1a1a24",
                border: "1px solid #2a2a3a",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend />
            {summaries.map((s) => (
              <Line
                key={s.agent}
                type="monotone"
                dataKey={s.agent}
                stroke={AGENT_COLORS[s.agent] || "#6366f1"}
                strokeWidth={2}
                dot={{ r: 3 }}
                name={s.agent}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Sector Comparison */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
        <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
          Win Rate by Sector
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={sectorComparison} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
            <XAxis dataKey="sector" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#1a1a24",
                border: "1px solid #2a2a3a",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend />
            {summaries.map((s) => (
              <Bar
                key={s.agent}
                dataKey={s.agent}
                fill={AGENT_COLORS[s.agent]}
                radius={[3, 3, 0, 0]}
                name={s.agent}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
