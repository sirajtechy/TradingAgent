"use client";

import { AgentName } from "@/app/lib/types";

const AGENTS: { value: AgentName | "all"; label: string; color: string }[] = [
  { value: "all", label: "All Agents", color: "bg-gray-600" },
  { value: "technical", label: "Technical", color: "bg-blue-600" },
  { value: "fundamental", label: "Fundamental", color: "bg-emerald-600" },
  { value: "orchestrator", label: "Orchestrator", color: "bg-purple-600" },
];

const SECTORS = [
  "all",
  "Technology",
  "Healthcare",
  "Financials",
  "Consumer_Staples",
  "Energy",
];

const SIGNALS = ["all", "BUY", "SELL", "HOLD"];
const CORRECTNESS = [
  { value: "all", label: "All" },
  { value: "correct", label: "Correct ✅" },
  { value: "incorrect", label: "Incorrect ❌" },
  { value: "neutral", label: "Neutral ➖" },
];

interface FilterBarProps {
  agent: AgentName | "all";
  sector: string;
  signal: string;
  correct: string;
  ticker: string;
  month: string;
  tickers: string[];
  months: string[];
  onAgentChange: (v: AgentName | "all") => void;
  onSectorChange: (v: string) => void;
  onSignalChange: (v: string) => void;
  onCorrectChange: (v: string) => void;
  onTickerChange: (v: string) => void;
  onMonthChange: (v: string) => void;
}

export default function FilterBar({
  agent, sector, signal, correct, ticker, month, tickers, months,
  onAgentChange, onSectorChange, onSignalChange, onCorrectChange,
  onTickerChange, onMonthChange,
}: FilterBarProps) {
  const selectClass =
    "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent";

  return (
    <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-900/50 backdrop-blur rounded-xl border border-gray-800">
      {/* Agent Tabs */}
      <div className="flex gap-1 mr-2">
        {AGENTS.map((a) => (
          <button
            key={a.value}
            onClick={() => onAgentChange(a.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              agent === a.value
                ? `${a.color} text-white shadow-lg`
                : "bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>

      <div className="h-6 w-px bg-gray-700" />

      <select value={sector} onChange={(e) => onSectorChange(e.target.value)} className={selectClass}>
        {SECTORS.map((s) => (
          <option key={s} value={s}>{s === "all" ? "All Sectors" : s.replace("_", " ")}</option>
        ))}
      </select>

      <select value={signal} onChange={(e) => onSignalChange(e.target.value)} className={selectClass}>
        {SIGNALS.map((s) => (
          <option key={s} value={s}>{s === "all" ? "All Signals" : s}</option>
        ))}
      </select>

      <select value={correct} onChange={(e) => onCorrectChange(e.target.value)} className={selectClass}>
        {CORRECTNESS.map((c) => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </select>

      <select value={ticker} onChange={(e) => onTickerChange(e.target.value)} className={selectClass}>
        <option value="all">All Tickers</option>
        {tickers.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>

      <select value={month} onChange={(e) => onMonthChange(e.target.value)} className={selectClass}>
        <option value="all">All Months</option>
        {months.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    </div>
  );
}
