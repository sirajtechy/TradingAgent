"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { getDashboardData, getSignals, getAllTickers, getAllMonths, computeMetrics } from "@/app/lib/data";
import { AgentName, Signal } from "@/app/lib/types";
import FilterBar from "@/app/components/FilterBar";
import StatCard from "@/app/components/StatCard";
import AgentComparisonGrid from "@/app/components/AgentComparisonGrid";
import ConfusionMatrix from "@/app/components/ConfusionMatrix";
import BarChart from "@/app/components/BarChart";
import SignalTable from "@/app/components/SignalTable";
import MisclassificationExplorer from "@/app/components/MisclassificationExplorer";
import PredictionsView from "@/app/components/PredictionsView";

type Tab = "predictions" | "overview" | "confusion" | "signals" | "misclass";

export default function Dashboard() {
  const data = getDashboardData();
  const tickers = getAllTickers();
  const months = getAllMonths();

  // Filters
  const [agent, setAgent] = useState<AgentName | "all">("all");
  const [sector, setSector] = useState("all");
  const [signal, setSignal] = useState("all");
  const [correct, setCorrect] = useState("all");
  const [ticker, setTicker] = useState("all");
  const [month, setMonth] = useState("all");
  const [tab, setTab] = useState<Tab>("predictions");

  // Filtered signals
  const filtered = useMemo(() => {
    let s = data.signals;
    if (agent !== "all") s = s.filter((x) => x.agent === agent);
    if (sector !== "all") s = s.filter((x) => x.sector === sector);
    if (signal !== "all") s = s.filter((x) => x.signal === signal);
    if (ticker !== "all") s = s.filter((x) => x.ticker === ticker);
    if (month !== "all") s = s.filter((x) => x.month === month);
    if (correct === "correct") s = s.filter((x) => x.correct === true);
    else if (correct === "incorrect") s = s.filter((x) => x.correct === false);
    else if (correct === "neutral") s = s.filter((x) => x.correct === null);
    return s;
  }, [data.signals, agent, sector, signal, correct, ticker, month]);

  const metrics = useMemo(() => computeMetrics(filtered), [filtered]);

  // Sector win rates for bar chart
  const sectorWinRates = useMemo(() => {
    const colors: Record<string, string> = {
      Technology: "#3b82f6",
      Healthcare: "#ef4444",
      Financials: "#f59e0b",
      Consumer_Staples: "#10b981",
      Energy: "#8b5cf6",
    };
    return data.meta.sectors.map((sec) => {
      const secSignals = filtered.filter((s) => s.sector === sec);
      const trades = secSignals.filter((s) => s.signal !== "HOLD");
      const corrects = trades.filter((s) => s.correct === true);
      return {
        label: sec,
        value: trades.length ? (corrects.length / trades.length) * 100 : 0,
        color: colors[sec] || "#6b7280",
      };
    });
  }, [filtered, data.meta.sectors]);

  // Monthly performance for bar chart
  const monthlyPerf = useMemo(() => {
    return months.map((m) => {
      const mSignals = filtered.filter((s) => s.month === m && s.signal !== "HOLD");
      const corrects = mSignals.filter((s) => s.correct === true);
      return {
        label: m.replace(/\s\d{4}/, "").slice(0, 3),
        value: mSignals.length ? (corrects.length / mSignals.length) * 100 : 0,
        color: "#3b82f6",
      };
    });
  }, [filtered, months]);

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "predictions", label: "🔮 Predictions" },
    { key: "overview", label: "Overview" },
    { key: "confusion", label: "Confusion Matrix" },
    { key: "signals", label: "Signal Log", count: filtered.length },
    { key: "misclass", label: "Misclassifications", count: filtered.filter((s) => s.correct === false).length },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-100">
                Trading Dashboard
              </h1>
              <p className="text-xs text-gray-500 mt-0.5">
                {data.meta.window} · {data.meta.months} months · {data.signals.length} total signals
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/backtest"
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                Backtest Runner →
              </Link>
              <div className="text-right">
                <p className="text-xs text-gray-500">Generated</p>
                <p className="text-sm font-mono text-gray-400">{data.meta.generated}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1600px] mx-auto px-6 py-6 w-full space-y-6">
        {/* Filters */}
        <FilterBar
          agent={agent} sector={sector} signal={signal} correct={correct}
          ticker={ticker} month={month} tickers={tickers} months={months}
          onAgentChange={setAgent} onSectorChange={setSector}
          onSignalChange={setSignal} onCorrectChange={setCorrect}
          onTickerChange={setTicker} onMonthChange={setMonth}
        />

        {/* Tab navigation */}
        <div className="flex gap-1 border-b border-gray-800 pb-0">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              {t.label}
              {t.count !== undefined && (
                <span className="ml-2 text-xs bg-gray-800 px-2 py-0.5 rounded-full">{t.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "predictions" && <PredictionsView />}

        {tab === "overview" && (
          <div className="space-y-6">
            {/* Stat cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              <StatCard label="Win Rate" value={metrics.winRate != null ? `${metrics.winRate}%` : "N/A"} color={metrics.winRate != null && metrics.winRate >= 55 ? "emerald" : metrics.winRate != null && metrics.winRate >= 50 ? "amber" : "red"} />
              <StatCard label="Total Trades" value={metrics.totalTrades} color="blue" />
              <StatCard label="Correct" value={metrics.correct} color="emerald" />
              <StatCard label="Incorrect" value={metrics.incorrect} color="red" />
              <StatCard label="Sharpe Ratio" value={metrics.sharpe ?? "N/A"} color={metrics.sharpe != null && metrics.sharpe > 0.5 ? "emerald" : "amber"} />
              <StatCard label="Profit Factor" value={metrics.profitFactor ?? "N/A"} color={metrics.profitFactor != null && metrics.profitFactor > 1.5 ? "emerald" : "amber"} />
              <StatCard label="Max Drawdown" value={metrics.maxDrawdown != null ? `${metrics.maxDrawdown}%` : "N/A"} color="red" />
            </div>

            {/* Agent comparison */}
            <AgentComparisonGrid summaries={data.summaries} />

            {/* Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <BarChart data={sectorWinRates} title="Win Rate by Sector" />
              <BarChart data={monthlyPerf} title="Monthly Win Rate" />
            </div>
          </div>
        )}

        {tab === "confusion" && (
          <div className="space-y-6">
            {/* Overall confusion matrix */}
            <ConfusionMatrix cm={metrics.cm} title="Overall Confusion Matrix (Filtered)" />

            {/* Per-agent if showing all */}
            {agent === "all" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(["technical", "fundamental", "orchestrator"] as AgentName[]).map((a) => {
                  const agentSignals = filtered.filter((s) => s.agent === a);
                  const am = computeMetrics(agentSignals);
                  return <ConfusionMatrix key={a} cm={am.cm} title={`${a.charAt(0).toUpperCase() + a.slice(1)} Agent`} />;
                })}
              </div>
            )}

            {/* Per-sector */}
            <h3 className="text-sm font-semibold text-gray-400 mt-4">By Sector</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {data.meta.sectors.map((sec) => {
                const secSignals = filtered.filter((s) => s.sector === sec);
                const sm = computeMetrics(secSignals);
                return <ConfusionMatrix key={sec} cm={sm.cm} title={sec.replace("_", " ")} />;
              })}
            </div>
          </div>
        )}

        {tab === "signals" && <SignalTable signals={filtered} />}

        {tab === "misclass" && <MisclassificationExplorer signals={filtered} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-600">
        Backtest Dashboard · {data.meta.window} · {data.summaries.length} agents · {data.signals.length} signals
      </footer>
    </div>
  );
}
