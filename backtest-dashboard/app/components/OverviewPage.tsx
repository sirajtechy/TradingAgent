"use client";

import type { DashboardData, PredictionData } from "../lib/types";
import { useMemo } from "react";
import { winRate } from "../lib/data-utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

interface Props {
  dashboard: DashboardData;
  predictions: PredictionData;
  onTickerClick: (ticker: string) => void;
}

const SIGNAL_COLORS: Record<string, string> = {
  BUY: "#22c55e",
  SELL: "#ef4444",
  HOLD: "#eab308",
  bullish: "#22c55e",
  bearish: "#ef4444",
  neutral: "#eab308",
};

function StatCard({
  label,
  value,
  sub,
  color = "indigo",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colors: Record<string, string> = {
    indigo: "from-indigo-500/20 to-indigo-600/5 border-indigo-500/30",
    green: "from-green-500/20 to-green-600/5 border-green-500/30",
    red: "from-red-500/20 to-red-600/5 border-red-500/30",
    yellow: "from-yellow-500/20 to-yellow-600/5 border-yellow-500/30",
    cyan: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/30",
    purple: "from-purple-500/20 to-purple-600/5 border-purple-500/30",
  };
  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-4 ${colors[color] || colors.indigo}`}
    >
      <p className="text-xs text-[var(--text-dim)] uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-[var(--text-dim)] mt-1">{sub}</p>}
    </div>
  );
}

export default function OverviewPage({ dashboard, predictions, onTickerClick }: Props) {
  const { summaries, signals, meta } = dashboard;
  const { summary: predSummary, sectorSummaries, predictions: predList } = predictions;

  // Per-agent stats
  const agentStats = useMemo(
    () =>
      summaries.map((s) => ({
        agent: s.agent,
        winRate: s.winRate ?? 0,
        trades: s.totalTrades,
        buys: s.buys,
        sells: s.sells,
        holds: s.holds,
      })),
    [summaries]
  );

  // Sector performance
  const sectorData = useMemo(() => {
    const sectors = meta.sectors || [];
    return sectors.map((sec) => {
      const secSignals = signals.filter((s) => s.sector === sec);
      return {
        sector: sec.replace("_", " "),
        winRate: Math.round(winRate(secSignals) * 10) / 10,
        trades: secSignals.filter((s) => s.signal !== "HOLD").length,
      };
    });
  }, [signals, meta.sectors]);

  // Signal distribution across all agents
  const signalDist = useMemo(() => {
    const buys = signals.filter((s) => s.signal === "BUY").length;
    const sells = signals.filter((s) => s.signal === "SELL").length;
    const holds = signals.filter((s) => s.signal === "HOLD").length;
    return [
      { name: "BUY", value: buys },
      { name: "SELL", value: sells },
      { name: "HOLD", value: holds },
    ];
  }, [signals]);

  // Top & bottom tickers by return
  const tickerPerformance = useMemo(() => {
    const byTicker: Record<string, number[]> = {};
    signals.forEach((s) => {
      if (s.signal === "HOLD") return;
      if (!byTicker[s.ticker]) byTicker[s.ticker] = [];
      byTicker[s.ticker].push(s.returnPct);
    });
    const entries = Object.entries(byTicker).map(([t, rets]) => ({
      ticker: t,
      avgReturn: rets.reduce((a, b) => a + b, 0) / rets.length,
    }));
    entries.sort((a, b) => b.avgReturn - a.avgReturn);
    return entries;
  }, [signals]);

  // Sector prediction heatmap data
  const sectorPredData = useMemo(() => {
    return Object.entries(sectorSummaries).map(([sec, d]) => ({
      sector: sec.replace("_", " "),
      bullish: d.bullish,
      bearish: d.bearish,
      neutral: d.neutral,
      avgScore: d.avgScore,
      dominant: d.dominant,
    }));
  }, [sectorSummaries]);

  // High confidence setups — deduplicated by ticker (keep highest confidence per ticker)
  const highConf = (() => {
    const seen = new Map<string, typeof predList[0]>();
    for (const p of predList) {
      if (p.confidence < 0.7) continue;
      const existing = seen.get(p.ticker);
      if (!existing || p.confidence > existing.confidence) seen.set(p.ticker, p);
    }
    return [...seen.values()].sort((a, b) => b.confidence - a.confidence).slice(0, 8);
  })();

  const totalSignals = signals.length;
  const totalTrades = signals.filter((s) => s.signal !== "HOLD").length;
  const overallWR = winRate(signals);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard Overview</h1>
          <p className="text-sm text-[var(--text-dim)]">
            {meta.window} · {meta.months} months · {meta.sectors.length} sectors · Generated{" "}
            {meta.generated}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
            Live Predictions: {predictions.meta.date}
          </span>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Signals" value={totalSignals} sub={`${totalTrades} trades`} />
        <StatCard
          label="Overall Win Rate"
          value={`${overallWR.toFixed(1)}%`}
          color={overallWR >= 55 ? "green" : overallWR >= 50 ? "yellow" : "red"}
        />
        <StatCard
          label="Bullish"
          value={predSummary.bullish}
          sub={`of ${predictions.meta.totalTickers}`}
          color="green"
        />
        <StatCard
          label="Bearish"
          value={predSummary.bearish}
          sub={`of ${predictions.meta.totalTickers}`}
          color="red"
        />
        <StatCard
          label="Agreement Rate"
          value={`${predSummary.agreementRate}%`}
          sub={`${predSummary.conflictCount} conflicts`}
          color="cyan"
        />
        <StatCard
          label="Avg Score"
          value={predSummary.avgScore.toFixed(1)}
          color="purple"
        />
      </div>

      {/* Row: Agent Performance + Signal Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent Win Rates */}
        <div className="lg:col-span-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            Agent Performance
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={agentStats} barCategoryGap="20%">
              <XAxis dataKey="agent" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="winRate" name="Win Rate %" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Signal Pie */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            Signal Distribution
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={signalDist}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ name, value }) => `${name}: ${value}`}
              >
                {signalDist.map((entry) => (
                  <Cell key={entry.name} fill={SIGNAL_COLORS[entry.name]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row: Sector Performance + Sector Predictions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Win Rates */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            Sector Win Rates (Backtest)
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sectorData} layout="vertical" barCategoryGap="15%">
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="sector"
                width={120}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="winRate" fill="#22c55e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sector Predictions Heatmap */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            Sector Sentiment (Predictions)
          </h2>
          <div className="space-y-2">
            {sectorPredData.map((s) => {
              const total = s.bullish + s.bearish + s.neutral;
              return (
                <div key={s.sector} className="flex items-center gap-3">
                  <span className="text-xs w-28 truncate text-[var(--text-dim)]">{s.sector}</span>
                  <div className="flex-1 flex h-6 rounded-md overflow-hidden">
                    {s.bullish > 0 && (
                      <div
                        className="bg-green-500/70 flex items-center justify-center text-[10px] font-medium"
                        style={{ width: `${(s.bullish / total) * 100}%` }}
                      >
                        {s.bullish}
                      </div>
                    )}
                    {s.neutral > 0 && (
                      <div
                        className="bg-yellow-500/50 flex items-center justify-center text-[10px] font-medium"
                        style={{ width: `${(s.neutral / total) * 100}%` }}
                      >
                        {s.neutral}
                      </div>
                    )}
                    {s.bearish > 0 && (
                      <div
                        className="bg-red-500/70 flex items-center justify-center text-[10px] font-medium"
                        style={{ width: `${(s.bearish / total) * 100}%` }}
                      >
                        {s.bearish}
                      </div>
                    )}
                  </div>
                  <span className="text-xs w-10 text-right text-[var(--text-dim)]">
                    {s.avgScore.toFixed(0)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Row: Top Performers + High Confidence Setups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top/Bottom Tickers */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            Top & Bottom Tickers (Avg Return)
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-green-400 mb-2 font-medium">Top 5</p>
              {tickerPerformance.slice(0, 5).map((t) => (
                <button
                  key={t.ticker}
                  onClick={() => onTickerClick(t.ticker)}
                  className="flex w-full items-center justify-between py-1.5 px-2 rounded hover:bg-white/5 transition-colors"
                >
                  <span className="text-sm font-mono">{t.ticker}</span>
                  <span className="text-sm text-green-400 font-medium">
                    +{t.avgReturn.toFixed(1)}%
                  </span>
                </button>
              ))}
            </div>
            <div>
              <p className="text-xs text-red-400 mb-2 font-medium">Bottom 5</p>
              {tickerPerformance.slice(-5).reverse().map((t) => (
                <button
                  key={t.ticker}
                  onClick={() => onTickerClick(t.ticker)}
                  className="flex w-full items-center justify-between py-1.5 px-2 rounded hover:bg-white/5 transition-colors"
                >
                  <span className="text-sm font-mono">{t.ticker}</span>
                  <span className="text-sm text-red-400 font-medium">
                    {t.avgReturn.toFixed(1)}%
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* High Confidence Setups */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-sm font-semibold mb-4 text-[var(--text-dim)] uppercase tracking-wider">
            High Confidence Setups (Live)
          </h2>
          {highConf.length === 0 ? (
            <p className="text-sm text-[var(--text-dim)]">No high confidence setups found.</p>
          ) : (
            <div className="space-y-2">
              {highConf.map((p) => (
                <button
                  key={p.ticker}
                  onClick={() => onTickerClick(p.ticker)}
                  className="w-full flex items-center justify-between py-2 px-3 rounded-lg bg-white/3 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono font-bold">{p.ticker}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        p.signalLabel === "BUY"
                          ? "bg-green-500/20 text-green-400"
                          : p.signalLabel === "SELL"
                          ? "bg-red-500/20 text-red-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}
                    >
                      {p.signalLabel}
                    </span>
                    <span className="text-xs text-[var(--text-dim)]">{p.sector}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-[var(--text-dim)]">
                      Score: {p.orchestratorScore.toFixed(0)}
                    </span>
                    <span className="text-xs font-medium text-indigo-400">
                      {(p.confidence * 100).toFixed(0)}% conf
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
