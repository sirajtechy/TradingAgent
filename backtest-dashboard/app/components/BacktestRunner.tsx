"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  processBacktestFiles,
  detectAgent,
  detectTicker,
  UploadedFile,
} from "@/app/lib/process-backtest";
import { exportToExcel } from "@/app/lib/excel-export";
import { computeMetrics } from "@/app/lib/data-utils";
import { DashboardData, AgentName } from "@/app/lib/types";
import StatCard from "@/app/components/StatCard";
import AgentComparisonGrid from "@/app/components/AgentComparisonGrid";
import ConfusionMatrix from "@/app/components/ConfusionMatrix";
import BarChart from "@/app/components/BarChart";
import SignalTable from "@/app/components/SignalTable";
import MisclassificationExplorer from "@/app/components/MisclassificationExplorer";
import FilterBar from "@/app/components/FilterBar";

type Tab = "overview" | "confusion" | "signals" | "misclass";

export default function BacktestRunner() {
  // Upload state
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Filter state
  const [agent, setAgent] = useState<AgentName | "all">("all");
  const [sector, setSector] = useState("all");
  const [signal, setSignal] = useState("all");
  const [correct, setCorrect] = useState("all");
  const [ticker, setTicker] = useState("all");
  const [month, setMonth] = useState("all");
  const [tab, setTab] = useState<Tab>("overview");

  /* ── File handling ─────────────────────────────────────── */

  const handleFiles = useCallback(async (fileList: FileList) => {
    setError(null);
    setIsProcessing(true);

    const newFiles: UploadedFile[] = [];
    const errors: string[] = [];

    for (const file of Array.from(fileList)) {
      if (!file.name.endsWith(".json")) {
        errors.push(`${file.name}: not a JSON file`);
        continue;
      }
      try {
        const text = await file.text();
        const data = JSON.parse(text);

        // Validate structure
        if (!data.periods || !Array.isArray(data.periods)) {
          errors.push(`${file.name}: missing "periods" array`);
          continue;
        }

        newFiles.push({ name: file.name, data });
      } catch {
        errors.push(`${file.name}: invalid JSON`);
      }
    }

    if (errors.length > 0) {
      setError(errors.join("\n"));
    }

    if (newFiles.length > 0) {
      const allFiles = [...uploadedFiles, ...newFiles];
      setUploadedFiles(allFiles);

      // Process immediately
      const result = processBacktestFiles(allFiles);
      setDashboardData(result);
    }

    setIsProcessing(false);
  }, [uploadedFiles]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
      }
    },
    [handleFiles]
  );

  const clearAll = useCallback(() => {
    setUploadedFiles([]);
    setDashboardData(null);
    setError(null);
    setAgent("all");
    setSector("all");
    setSignal("all");
    setCorrect("all");
    setTicker("all");
    setMonth("all");
    setTab("overview");
  }, []);

  const removeFile = useCallback(
    (index: number) => {
      const updated = uploadedFiles.filter((_, i) => i !== index);
      setUploadedFiles(updated);
      if (updated.length > 0) {
        setDashboardData(processBacktestFiles(updated));
      } else {
        setDashboardData(null);
      }
    },
    [uploadedFiles]
  );

  /* ── Derived data ──────────────────────────────────────── */

  const tickers = useMemo(
    () =>
      dashboardData
        ? [...new Set(dashboardData.signals.map((s) => s.ticker))].sort()
        : [],
    [dashboardData]
  );

  const months = useMemo(() => {
    if (!dashboardData) return [];
    const seen = new Set<string>();
    const result: string[] = [];
    for (const s of dashboardData.signals) {
      if (!seen.has(s.month)) {
        seen.add(s.month);
        result.push(s.month);
      }
    }
    return result;
  }, [dashboardData]);

  const filtered = useMemo(() => {
    if (!dashboardData) return [];
    let s = dashboardData.signals;
    if (agent !== "all") s = s.filter((x) => x.agent === agent);
    if (sector !== "all") s = s.filter((x) => x.sector === sector);
    if (signal !== "all") s = s.filter((x) => x.signal === signal);
    if (ticker !== "all") s = s.filter((x) => x.ticker === ticker);
    if (month !== "all") s = s.filter((x) => x.month === month);
    if (correct === "correct") s = s.filter((x) => x.correct === true);
    else if (correct === "incorrect") s = s.filter((x) => x.correct === false);
    else if (correct === "neutral") s = s.filter((x) => x.correct === null);
    return s;
  }, [dashboardData, agent, sector, signal, correct, ticker, month]);

  const metrics = useMemo(() => computeMetrics(filtered), [filtered]);

  const sectorWinRates = useMemo(() => {
    if (!dashboardData) return [];
    const colors: Record<string, string> = {
      Technology: "#3b82f6",
      Healthcare: "#ef4444",
      Financials: "#f59e0b",
      Consumer_Staples: "#10b981",
      Energy: "#8b5cf6",
    };
    return dashboardData.meta.sectors.map((sec) => {
      const secSignals = filtered.filter((s) => s.sector === sec);
      const trades = secSignals.filter((s) => s.signal !== "HOLD");
      const corrects = trades.filter((s) => s.correct === true);
      return {
        label: sec,
        value: trades.length ? (corrects.length / trades.length) * 100 : 0,
        color: colors[sec] || "#6b7280",
      };
    });
  }, [filtered, dashboardData]);

  const monthlyPerf = useMemo(() => {
    return months.map((m) => {
      const mSignals = filtered.filter(
        (s) => s.month === m && s.signal !== "HOLD"
      );
      const corrects = mSignals.filter((s) => s.correct === true);
      return {
        label: m.replace(/\s\d{4}/, "").slice(0, 3),
        value: mSignals.length
          ? (corrects.length / mSignals.length) * 100
          : 0,
        color: "#3b82f6",
      };
    });
  }, [filtered, months]);

  /* ── File summary for uploaded list ────────────────────── */

  const fileSummaries = useMemo(() => {
    return uploadedFiles.map((f) => {
      const ag = detectAgent(f.name);
      const tk = f.data.ticker || detectTicker(f.name) || "?";
      return {
        name: f.name,
        ticker: tk,
        agent: ag || "unknown",
        periods: f.data.periods.length,
      };
    });
  }, [uploadedFiles]);

  /* ── Tabs ──────────────────────────────────────────────── */

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "overview", label: "Overview" },
    { key: "confusion", label: "Confusion Matrix" },
    { key: "signals", label: "Signal Log", count: filtered.length },
    {
      key: "misclass",
      label: "Misclassifications",
      count: filtered.filter((s) => s.correct === false).length,
    },
  ];

  /* ── Render: Upload Zone ───────────────────────────────── */

  if (!dashboardData) {
    return (
      <div className="flex flex-col min-h-screen">
        <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-[1600px] mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-100">
                  Backtest Runner
                </h1>
                <p className="text-xs text-gray-500 mt-0.5">
                  Upload backtest JSON results to analyze
                </p>
              </div>
              <Link
                href="/"
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                ← Dashboard
              </Link>
            </div>
          </div>
        </header>

        <main className="flex-1 max-w-[1600px] mx-auto px-6 py-12 w-full">
          <div className="max-w-2xl mx-auto space-y-8">
            {/* Upload drop zone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-12 text-center transition-all ${
                dragOver
                  ? "border-blue-500 bg-blue-500/10"
                  : "border-gray-700 hover:border-gray-500"
              }`}
            >
              <div className="space-y-4">
                <div className="text-4xl">📊</div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-200">
                    Drop backtest JSON files here
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">
                    or click to browse. Accepts *_technical_backtest_results.json,
                    *_backtest_results.json, *_orchestrator_backtest.json
                  </p>
                </div>
                <label className="inline-block cursor-pointer">
                  <span className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">
                    Browse Files
                  </span>
                  <input
                    type="file"
                    multiple
                    accept=".json"
                    onChange={handleInputChange}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* How it works */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-semibold text-gray-300">
                How It Works
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="space-y-1">
                  <div className="text-blue-400 font-mono">1. Upload</div>
                  <p className="text-gray-500">
                    Drop the per-ticker JSON files from your backtest output
                    directory
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="text-emerald-400 font-mono">2. Analyze</div>
                  <p className="text-gray-500">
                    Signals are extracted, aggregated, and confusion matrices
                    computed automatically
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="text-purple-400 font-mono">3. Export</div>
                  <p className="text-gray-500">
                    View results in the dashboard or export to Excel
                  </p>
                </div>
              </div>
            </div>

            {/* Supported file formats */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                Supported File Formats
              </h3>
              <div className="space-y-2 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <span className="text-blue-400">●</span>
                  <code className="text-gray-400">
                    AAPL_technical_backtest_results.json
                  </code>
                  <span>→ Technical Agent</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-emerald-400">●</span>
                  <code className="text-gray-400">
                    AAPL_backtest_results.json
                  </code>
                  <span>→ Fundamental Agent</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-purple-400">●</span>
                  <code className="text-gray-400">
                    AAPL_orchestrator_backtest.json
                  </code>
                  <span>→ Orchestrator</span>
                </div>
              </div>
            </div>

            {isProcessing && (
              <div className="text-center text-gray-400 text-sm">
                Processing files...
              </div>
            )}

            {error && (
              <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 text-sm text-red-400 whitespace-pre-line">
                {error}
              </div>
            )}
          </div>
        </main>
      </div>
    );
  }

  /* ── Render: Results Dashboard ─────────────────────────── */

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-100">
                Backtest Results
              </h1>
              <p className="text-xs text-gray-500 mt-0.5">
                {dashboardData.meta.window} · {dashboardData.meta.months} months
                · {dashboardData.signals.length} signals from{" "}
                {uploadedFiles.length} files
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
              >
                ← Dashboard
              </Link>
              <button
                onClick={() => exportToExcel(dashboardData)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Export Excel
              </button>
              <button
                onClick={clearAll}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition-colors"
              >
                Clear & Upload New
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1600px] mx-auto px-6 py-6 w-full space-y-6">
        {/* Uploaded files summary */}
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-300">
              Uploaded Files ({fileSummaries.length})
            </h3>
            <label className="cursor-pointer text-xs text-blue-400 hover:text-blue-300 transition-colors">
              + Add more files
              <input
                type="file"
                multiple
                accept=".json"
                onChange={handleInputChange}
                className="hidden"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            {fileSummaries.map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-1.5 text-xs"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    f.agent === "technical"
                      ? "bg-blue-400"
                      : f.agent === "fundamental"
                      ? "bg-emerald-400"
                      : f.agent === "orchestrator"
                      ? "bg-purple-400"
                      : "bg-gray-400"
                  }`}
                />
                <span className="font-mono text-gray-300">{f.ticker}</span>
                <span className="text-gray-600">{f.agent}</span>
                <span className="text-gray-600">({f.periods}m)</span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-gray-600 hover:text-red-400 transition-colors ml-1"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Filters */}
        <FilterBar
          agent={agent}
          sector={sector}
          signal={signal}
          correct={correct}
          ticker={ticker}
          month={month}
          tickers={tickers}
          months={months}
          onAgentChange={setAgent}
          onSectorChange={setSector}
          onSignalChange={setSignal}
          onCorrectChange={setCorrect}
          onTickerChange={setTicker}
          onMonthChange={setMonth}
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
                <span className="ml-2 text-xs bg-gray-800 px-2 py-0.5 rounded-full">
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              <StatCard
                label="Win Rate"
                value={
                  metrics.winRate != null ? `${metrics.winRate}%` : "N/A"
                }
                color={
                  metrics.winRate != null && metrics.winRate >= 55
                    ? "emerald"
                    : metrics.winRate != null && metrics.winRate >= 50
                    ? "amber"
                    : "red"
                }
              />
              <StatCard
                label="Total Trades"
                value={metrics.totalTrades}
                color="blue"
              />
              <StatCard
                label="Correct"
                value={metrics.correct}
                color="emerald"
              />
              <StatCard
                label="Incorrect"
                value={metrics.incorrect}
                color="red"
              />
              <StatCard
                label="Sharpe Ratio"
                value={metrics.sharpe ?? "N/A"}
                color={
                  metrics.sharpe != null && metrics.sharpe > 0.5
                    ? "emerald"
                    : "amber"
                }
              />
              <StatCard
                label="Profit Factor"
                value={metrics.profitFactor ?? "N/A"}
                color={
                  metrics.profitFactor != null && metrics.profitFactor > 1.5
                    ? "emerald"
                    : "amber"
                }
              />
              <StatCard
                label="Max Drawdown"
                value={
                  metrics.maxDrawdown != null
                    ? `${metrics.maxDrawdown}%`
                    : "N/A"
                }
                color="red"
              />
            </div>

            <AgentComparisonGrid summaries={dashboardData.summaries} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <BarChart data={sectorWinRates} title="Win Rate by Sector" />
              <BarChart data={monthlyPerf} title="Monthly Win Rate" />
            </div>
          </div>
        )}

        {tab === "confusion" && (
          <div className="space-y-6">
            <ConfusionMatrix
              cm={metrics.cm}
              title="Overall Confusion Matrix (Filtered)"
            />

            {agent === "all" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(
                  ["technical", "fundamental", "orchestrator"] as AgentName[]
                ).map((a) => {
                  const agentSignals = filtered.filter((s) => s.agent === a);
                  if (agentSignals.length === 0) return null;
                  const am = computeMetrics(agentSignals);
                  return (
                    <ConfusionMatrix
                      key={a}
                      cm={am.cm}
                      title={`${a.charAt(0).toUpperCase() + a.slice(1)} Agent`}
                    />
                  );
                })}
              </div>
            )}

            <h3 className="text-sm font-semibold text-gray-400 mt-4">
              By Sector
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {dashboardData.meta.sectors.map((sec) => {
                const secSignals = filtered.filter((s) => s.sector === sec);
                if (secSignals.length === 0) return null;
                const sm = computeMetrics(secSignals);
                return (
                  <ConfusionMatrix
                    key={sec}
                    cm={sm.cm}
                    title={sec.replace("_", " ")}
                  />
                );
              })}
            </div>
          </div>
        )}

        {tab === "signals" && <SignalTable signals={filtered} />}

        {tab === "misclass" && (
          <MisclassificationExplorer signals={filtered} />
        )}
      </main>

      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-600">
        Backtest Runner · {dashboardData.meta.window} ·{" "}
        {dashboardData.summaries.length} agents ·{" "}
        {dashboardData.signals.length} signals
      </footer>
    </div>
  );
}
