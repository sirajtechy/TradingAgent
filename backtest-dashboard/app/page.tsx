"use client";

import { useState } from "react";
import {
  BarChart3,
  LineChart,
  Target,
  TrendingUp,
  Table2,
  Brain,
  ChevronLeft,
  ChevronRight,
  Zap,
} from "lucide-react";
import { getDashboardData, getPredictionData, getAllSectors, getAllTickers, getAllMonths } from "./lib/data";
import OverviewPage from "./components/OverviewPage";
import PredictionsTable from "./components/PredictionsTable";
import StockDetail from "./components/StockDetail";
import AgentComparison from "./components/AgentComparison";
import SignalExplorer from "./components/SignalExplorer";
import MisclassificationView from "./components/MisclassificationView";

const dashboard = getDashboardData();
const predictions = getPredictionData();
const sectors = getAllSectors();
const tickers = getAllTickers();
const months = getAllMonths();

type Page = "overview" | "predictions" | "stock" | "agents" | "signals" | "misclass";

const NAV_ITEMS: { id: Page; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <BarChart3 size={18} /> },
  { id: "predictions", label: "Predictions", icon: <Target size={18} /> },
  { id: "stock", label: "Stock Detail", icon: <LineChart size={18} /> },
  { id: "agents", label: "Agent Comparison", icon: <Brain size={18} /> },
  { id: "signals", label: "Signal Explorer", icon: <Table2 size={18} /> },
  { id: "misclass", label: "Misclassifications", icon: <TrendingUp size={18} /> },
];

export default function Home() {
  const [page, setPage] = useState<Page>("overview");
  const [collapsed, setCollapsed] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState(tickers[0] || "AAPL");

  const navigateToStock = (ticker: string) => {
    setSelectedTicker(ticker);
    setPage("stock");
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-[var(--border)] bg-[var(--bg-card)] transition-all duration-200 ${
          collapsed ? "w-16" : "w-56"
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-4 border-b border-[var(--border)]">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
            T
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight truncate">Trading Agents</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                page === item.id
                  ? "bg-indigo-500/10 text-indigo-400 border-r-2 border-indigo-500"
                  : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
              }`}
            >
              <span className="shrink-0">{item.icon}</span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </button>
          ))}
          {/* External link to swing backtest */}
          <a
            href="/swing"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
          >
            <span className="shrink-0"><Zap size={18} /></span>
            {!collapsed && <span className="truncate">Swing 2026 ↗</span>}
          </a>
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center py-3 border-t border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)]"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1600px] mx-auto">
          {page === "overview" && (
            <OverviewPage
              dashboard={dashboard}
              predictions={predictions}
              onTickerClick={navigateToStock}
            />
          )}
          {page === "predictions" && (
            <PredictionsTable
              predictions={predictions}
              sectors={sectors}
              onTickerClick={navigateToStock}
            />
          )}
          {page === "stock" && (
            <StockDetail
              ticker={selectedTicker}
              signals={dashboard.signals}
              predictions={predictions}
              tickers={tickers}
              onTickerChange={setSelectedTicker}
            />
          )}
          {page === "agents" && (
            <AgentComparison
              summaries={dashboard.summaries}
              signals={dashboard.signals}
              months={months}
            />
          )}
          {page === "signals" && (
            <SignalExplorer
              signals={dashboard.signals}
              sectors={sectors}
              tickers={tickers}
              months={months}
              onTickerClick={navigateToStock}
            />
          )}
          {page === "misclass" && (
            <MisclassificationView
              signals={dashboard.signals}
              sectors={sectors}
              onTickerClick={navigateToStock}
            />
          )}
        </div>
      </main>
    </div>
  );
}
