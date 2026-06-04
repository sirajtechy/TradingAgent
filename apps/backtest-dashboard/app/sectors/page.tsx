"use client";

import { useEffect, useMemo, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  Target,
  ShieldAlert,
  Clock,
  Zap,
  BarChart3,
  Search,
  CheckCircle,
  XCircle,
  ArrowUpRight,
} from "lucide-react";
import Link from "next/link";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TradeSummary {
  ticker: string;
  sector: string;
  sentiment: "bullish" | "bearish" | "neutral";
  confidence_score: number;
  tech_score: number;
  fund_score: number;
  conflict: boolean;
  no_trade_reason: string | null;
  // trade fields (undefined for no-trades)
  entry_date?: string;
  entry_price?: number;
  entry_source?: string;
  exit_date?: string;
  exit_price?: number;
  exit_outcome?: "HIT_TARGET" | "HIT_STOP" | "OPEN" | "EXPIRED";
  holding_days?: number;
  gross_profit_pct?: number;
  net_profit_pct?: number;
  stop_loss?: number;
  target_price?: number;
  reward_risk_ratio?: number;
}

interface RunMeta {
  cutoff_date: string;
  target_days: number;
  run_date: string;
  elapsed_sec: number;
  total: number;
  trades: number;
  no_trades: number;
  errors: number;
}

interface SummaryData {
  run_meta: RunMeta;
  trades: TradeSummary[];
  no_trades: TradeSummary[];
  errors: { ticker: string; sector: string; error: string }[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const OUTCOME_CONFIG = {
  HIT_TARGET: { label: "HIT TARGET", bg: "bg-green-500/15", text: "text-green-400", border: "border-green-500/30", icon: <CheckCircle size={12} /> },
  HIT_STOP:   { label: "HIT STOP",   bg: "bg-red-500/15",   text: "text-red-400",   border: "border-red-500/30",   icon: <XCircle size={12} /> },
  OPEN:       { label: "OPEN",        bg: "bg-yellow-500/15",text: "text-yellow-400",border: "border-yellow-500/30",icon: <Zap size={12} /> },
  EXPIRED:    { label: "EXPIRED",     bg: "bg-blue-500/15",  text: "text-blue-400",  border: "border-blue-500/30",  icon: <Clock size={12} /> },
};

const SECTOR_COLORS: Record<string, string> = {
  Technology:       "text-indigo-400",
  Healthcare:       "text-cyan-400",
  Financials:       "text-purple-400",
  Consumer_Staples: "text-yellow-400",
  Energy:           "text-orange-400",
};

function formatDate(raw: string | undefined): string {
  if (!raw) return "—";
  const d = new Date(raw + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function ScoreBar({ value, color = "bg-indigo-500" }: { value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/5">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <span className="text-xs text-[var(--text-dim)] w-8 text-right">{value.toFixed(0)}</span>
    </div>
  );
}

function PatternBadge({ source }: { source: string }) {
  const name = source.replace("pattern:", "");
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 whitespace-nowrap">
      <ArrowUpRight size={10} />
      {name}
    </span>
  );
}

function SentimentIcon({ s }: { s: string }) {
  if (s === "bullish") return <TrendingUp size={14} className="text-green-400" />;
  if (s === "bearish") return <TrendingDown size={14} className="text-red-400" />;
  return <Minus size={14} className="text-[var(--text-dim)]" />;
}

// ─── Trade Card ───────────────────────────────────────────────────────────────

function TradeCard({ t }: { t: TradeSummary }) {
  const [open, setOpen] = useState(false);
  const outcome = t.exit_outcome as keyof typeof OUTCOME_CONFIG;
  const cfg = OUTCOME_CONFIG[outcome] ?? OUTCOME_CONFIG.OPEN;
  const upside = t.target_price && t.entry_price
    ? (((t.target_price - t.entry_price) / t.entry_price) * 100).toFixed(1)
    : null;
  const downside = t.stop_loss && t.entry_price
    ? (((t.entry_price - t.stop_loss) / t.entry_price) * 100).toFixed(1)
    : null;

  return (
    <div className={`rounded-xl border ${cfg.border} bg-[var(--bg-card)] overflow-hidden transition-all`}>
      {/* Header row */}
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/3 transition-colors text-left"
        onClick={() => setOpen((p) => !p)}
      >
        {/* Ticker + sector */}
        <div className="w-16 shrink-0">
          <div className="text-sm font-bold text-[var(--text)]">{t.ticker}</div>
          <div className={`text-[10px] font-medium ${SECTOR_COLORS[t.sector] ?? "text-[var(--text-dim)]"}`}>
            {t.sector.replace("_", " ")}
          </div>
        </div>

        {/* Outcome badge */}
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border} shrink-0`}>
          {cfg.icon}{cfg.label}
        </span>

        {/* Pattern */}
        {t.entry_source && <PatternBadge source={t.entry_source} />}

        {/* Date strip — always visible */}
        <div className="hidden lg:flex flex-col items-start gap-0.5 text-[10px] shrink-0">
          <span className="text-[var(--text-dim)]">
            <span className="text-[9px] uppercase tracking-wide mr-1 text-[var(--text-dim)]">Entry</span>
            <span className="font-mono text-[var(--text)]">{formatDate(t.entry_date)}</span>
          </span>
          <span className="text-[var(--text-dim)]">
            <span className="text-[9px] uppercase tracking-wide mr-1 text-[var(--text-dim)]">
              {outcome === "OPEN" ? "Exp" : "Exit"}
            </span>
            {outcome === "OPEN" ? (
              <span className="font-mono text-yellow-400">In progress</span>
            ) : (
              <span className="font-mono text-[var(--text)]">
                {formatDate(t.exit_date)}{t.holding_days ? <span className="text-[var(--text-dim)]"> · {t.holding_days}d</span> : null}
              </span>
            )}
          </span>
        </div>

        <div className="flex-1" />

        {/* Entry / Target / Stop mini-strip */}
        <div className="hidden sm:flex items-center gap-4 text-xs">
          <div className="text-center">
            <div className="text-[var(--text-dim)]">Entry</div>
            <div className="font-mono font-semibold">${t.entry_price?.toFixed(2)}</div>
          </div>
          <div className="text-center">
            <div className="text-green-400">Target</div>
            <div className="font-mono font-semibold text-green-400">${t.target_price?.toFixed(2)}</div>
          </div>
          <div className="text-center">
            <div className="text-red-400">Stop</div>
            <div className="font-mono font-semibold text-red-400">${t.stop_loss?.toFixed(2)}</div>
          </div>
          {t.reward_risk_ratio != null && (
            <div className="text-center">
              <div className="text-[var(--text-dim)]">R/R</div>
              <div className="font-mono font-semibold text-yellow-400">{t.reward_risk_ratio}x</div>
            </div>
          )}
        </div>

        {/* Confidence score */}
        <div className="hidden md:flex flex-col items-end ml-4 shrink-0 w-20">
          <div className="text-[10px] text-[var(--text-dim)] mb-0.5">Confidence</div>
          <ScoreBar value={t.confidence_score} />
        </div>

        <span className="ml-2 text-[var(--text-dim)] shrink-0">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-[var(--border)] px-4 py-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-xs">
          <div>
            <div className="text-[var(--text-dim)] mb-1">Entry Date</div>
            <div className="font-mono font-semibold">{formatDate(t.entry_date)}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">{outcome === "OPEN" ? "Exit Date (OPEN)" : "Exit Date"}</div>
            <div className={`font-mono font-semibold ${outcome === "OPEN" ? "text-yellow-400" : ""}`}>
              {outcome === "OPEN" ? "In progress" : formatDate(t.exit_date)}
            </div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Holding Days</div>
            <div className="font-mono font-semibold">{t.holding_days ?? 0}d{outcome === "OPEN" ? " (ongoing)" : ""}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Entry Price</div>
            <div className="font-mono font-semibold">${t.entry_price?.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Exit Price</div>
            <div className="font-mono font-semibold">{outcome === "OPEN" ? "—" : `$${t.exit_price?.toFixed(2)}`}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Target</div>
            <div className="font-mono text-green-400">${t.target_price?.toFixed(2)} {upside && <span className="text-green-500/70">(+{upside}%)</span>}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Stop Loss</div>
            <div className="font-mono text-red-400">${t.stop_loss?.toFixed(2)} {downside && <span className="text-red-500/70">(-{downside}%)</span>}</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Gross P&L</div>
            <div className={`font-mono font-semibold ${(t.gross_profit_pct ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
              {(t.gross_profit_pct ?? 0) >= 0 ? "+" : ""}{t.gross_profit_pct?.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Net P&L</div>
            <div className={`font-mono font-semibold ${(t.net_profit_pct ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
              {(t.net_profit_pct ?? 0) >= 0 ? "+" : ""}{t.net_profit_pct?.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Tech Score</div>
            <ScoreBar value={t.tech_score} color="bg-cyan-500" />
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Fund Score</div>
            <ScoreBar value={t.fund_score} color="bg-purple-500" />
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">R/R Ratio</div>
            <div className="font-mono text-yellow-400">{t.reward_risk_ratio ?? "—"}x</div>
          </div>
          <div>
            <div className="text-[var(--text-dim)] mb-1">Conflict</div>
            <div className={t.conflict ? "text-red-400" : "text-green-400"}>{t.conflict ? "Yes" : "No"}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── No-Trade Row ─────────────────────────────────────────────────────────────

function NoTradeRow({ t }: { t: TradeSummary }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)] transition-colors text-xs">
      <SentimentIcon s={t.sentiment} />
      <span className="font-bold w-12 text-[var(--text)]">{t.ticker}</span>
      <span className={`text-[10px] font-medium ${SECTOR_COLORS[t.sector] ?? "text-[var(--text-dim)]"} w-24`}>
        {t.sector.replace("_", " ")}
      </span>
      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold
        ${t.sentiment === "bullish" ? "bg-green-500/10 text-green-400" :
          t.sentiment === "bearish" ? "bg-red-500/10 text-red-400" :
          "bg-white/5 text-[var(--text-dim)]"}`}>
        {t.sentiment.toUpperCase()}
      </span>
      <div className="hidden sm:flex items-center gap-2 flex-1 min-w-0">
        <ScoreBar value={t.confidence_score} />
      </div>
      <span className="flex-1 text-[var(--text-dim)] truncate min-w-0">{t.no_trade_reason}</span>
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = "text-[var(--text)]" }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-4">
      <div className="text-xs text-[var(--text-dim)] mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-[var(--text-dim)] mt-0.5">{sub}</div>}
    </div>
  );
}

// ─── Sector Breakdown Bar ─────────────────────────────────────────────────────

function SectorBreakdown({ trades }: { trades: TradeSummary[] }) {
  const byS = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of trades) m[t.sector] = (m[t.sector] ?? 0) + 1;
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [trades]);
  const max = Math.max(...byS.map(([, n]) => n), 1);

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-4">
      <div className="text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-3">Trades by Sector</div>
      <div className="space-y-2">
        {byS.map(([sector, count]) => (
          <div key={sector} className="flex items-center gap-3 text-xs">
            <span className={`w-28 shrink-0 ${SECTOR_COLORS[sector] ?? "text-[var(--text-dim)]"}`}>
              {sector.replace("_", " ")}
            </span>
            <div className="flex-1 h-2 rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="w-4 text-right text-[var(--text-dim)]">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Pattern Breakdown ────────────────────────────────────────────────────────

function PatternBreakdown({ trades }: { trades: TradeSummary[] }) {
  const byP = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of trades) {
      const name = (t.entry_source ?? "").replace("pattern:", "");
      if (name) m[name] = (m[name] ?? 0) + 1;
    }
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [trades]);
  const max = Math.max(...byP.map(([, n]) => n), 1);

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-5 py-4">
      <div className="text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-3">Patterns Triggered</div>
      <div className="space-y-2">
        {byP.map(([pattern, count]) => (
          <div key={pattern} className="flex items-center gap-3 text-xs">
            <span className="w-36 shrink-0 text-indigo-300">{pattern}</span>
            <div className="flex-1 h-2 rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-indigo-400 transition-all"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="w-4 text-right text-[var(--text-dim)]">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SectorsPredictionsPage() {
  const [data, setData] = useState<SummaryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("All");
  const [tab, setTab] = useState<"trades" | "notrade">("trades");
  const [sortBy, setSortBy] = useState<"confidence" | "rr" | "ticker">("confidence");

  useEffect(() => {
    fetch("/api/sectors-predictions")
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError("Failed to load data"));
  }, []);

  const sectors = useMemo(() => {
    if (!data) return ["All"];
    const s = new Set([
      ...data.trades.map((t) => t.sector),
      ...data.no_trades.map((t) => t.sector),
    ]);
    return ["All", ...Array.from(s).sort()];
  }, [data]);

  const filteredTrades = useMemo(() => {
    if (!data) return [];
    return data.trades
      .filter((t) => {
        const matchSector = sectorFilter === "All" || t.sector === sectorFilter;
        const matchSearch = search === "" ||
          t.ticker.toLowerCase().includes(search.toLowerCase()) ||
          (t.entry_source ?? "").toLowerCase().includes(search.toLowerCase());
        return matchSector && matchSearch;
      })
      .sort((a, b) => {
        if (sortBy === "confidence") return b.confidence_score - a.confidence_score;
        if (sortBy === "rr") return (b.reward_risk_ratio ?? 0) - (a.reward_risk_ratio ?? 0);
        return a.ticker.localeCompare(b.ticker);
      });
  }, [data, search, sectorFilter, sortBy]);

  const filteredNoTrades = useMemo(() => {
    if (!data) return [];
    return data.no_trades.filter((t) => {
      const matchSector = sectorFilter === "All" || t.sector === sectorFilter;
      const matchSearch = search === "" || t.ticker.toLowerCase().includes(search.toLowerCase());
      return matchSector && matchSearch;
    });
  }, [data, search, sectorFilter]);

  if (error) return (
    <div className="min-h-screen flex items-center justify-center text-red-400">
      <div className="text-center">
        <div className="text-xl font-bold mb-2">Error loading data</div>
        <div className="text-sm text-[var(--text-dim)]">{error}</div>
      </div>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen flex items-center justify-center text-[var(--text-dim)]">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        Loading sector predictions…
      </div>
    </div>
  );

  const { run_meta, trades } = data;
  const hitTarget = trades.filter((t) => t.exit_outcome === "HIT_TARGET").length;
  const hitStop   = trades.filter((t) => t.exit_outcome === "HIT_STOP").length;
  const open      = trades.filter((t) => t.exit_outcome === "OPEN").length;
  const expired   = trades.filter((t) => t.exit_outcome === "EXPIRED").length;
  const closed    = hitTarget + hitStop + expired;
  const hitRate   = closed > 0 ? ((hitTarget / closed) * 100).toFixed(1) : "—";
  const avgRR     = trades.length > 0
    ? (trades.reduce((s, t) => s + (t.reward_risk_ratio ?? 0), 0) / trades.length).toFixed(2)
    : "—";
  const signalRate = ((run_meta.trades / run_meta.total) * 100).toFixed(0);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-[var(--text-dim)] hover:text-[var(--text)] transition-colors text-sm">
            <ChevronLeft size={16} />
            Dashboard
          </Link>
          <div className="h-4 w-px bg-[var(--border)]" />
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-indigo-400" />
            <span className="text-sm font-semibold">Sector Predictions</span>
          </div>
          <div className="flex items-center gap-2 ml-2 text-xs text-[var(--text-dim)]">
            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-[var(--border)]">
              Cutoff: {run_meta.cutoff_date}
            </span>
            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-[var(--border)]">
              {run_meta.target_days}-day window
            </span>
            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-[var(--border)]">
              50 tickers
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">

        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="Analyzed"     value={run_meta.total}    sub="tickers" />
          <StatCard label="Signals"      value={run_meta.trades}   sub={`${signalRate}% signal rate`} color="text-indigo-400" />
          <StatCard label="No Trade"     value={run_meta.no_trades} sub="filtered out" />
          <StatCard label="OPEN"         value={open}  sub="live setups"   color="text-yellow-400" />
          <StatCard label="Hit Rate"     value={closed > 0 ? `${hitRate}%` : "—"} sub={`${hitTarget} of ${closed} closed`} color="text-green-400" />
          <StatCard label="Avg R/R"      value={`${avgRR}x`} sub="reward/risk" color="text-yellow-400" />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SectorBreakdown trades={trades} />
          <PatternBreakdown trades={trades} />
        </div>

        {/* Outcome summary strip */}
        {trades.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {([
              ["OPEN",       open,      OUTCOME_CONFIG.OPEN],
              ["HIT_TARGET", hitTarget, OUTCOME_CONFIG.HIT_TARGET],
              ["EXPIRED",    expired,   OUTCOME_CONFIG.EXPIRED],
              ["HIT_STOP",   hitStop,   OUTCOME_CONFIG.HIT_STOP],
            ] as const).map(([label, count, cfg]) => (
              <div key={label} className={`rounded-xl border ${cfg.border} ${cfg.bg} px-4 py-3 flex items-center gap-3`}>
                <span className={`text-xl font-bold ${cfg.text}`}>{count}</span>
                <div>
                  <div className={`text-xs font-semibold ${cfg.text}`}>{cfg.label}</div>
                  <div className="text-[10px] text-[var(--text-dim)]">{label === "OPEN" ? "entries pending" : label === "HIT_TARGET" ? "winners" : label === "EXPIRED" ? "held full window" : "stopped out"}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Filters + search */}
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-48 max-w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-dim)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search ticker or pattern…"
              className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text)] placeholder-[var(--text-dim)] focus:outline-none focus:border-indigo-500"
            />
          </div>
          {/* Sector filter */}
          <div className="flex flex-wrap gap-1.5">
            {sectors.map((s) => (
              <button
                key={s}
                onClick={() => setSectorFilter(s)}
                className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                  sectorFilter === s
                    ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-300"
                    : "border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-white/5"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            ))}
          </div>
          {/* Sort (only for trades tab) */}
          {tab === "trades" && (
            <div className="flex gap-1.5 ml-auto">
              {(["confidence", "rr", "ticker"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                    sortBy === s
                      ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-300"
                      : "border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text)]"
                  }`}
                >
                  {s === "confidence" ? "Confidence ↓" : s === "rr" ? "R/R ↓" : "A–Z"}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[var(--border)] gap-0">
          {([
            { id: "trades",  label: `Active Signals (${filteredTrades.length})`,    icon: <Target size={14} /> },
            { id: "notrade", label: `No Trade (${filteredNoTrades.length})`,         icon: <ShieldAlert size={14} /> },
          ] as const).map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors ${
                tab === t.id
                  ? "border-indigo-500 text-[var(--text)]"
                  : "border-transparent text-[var(--text-dim)] hover:text-[var(--text)]"
              }`}
            >
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {tab === "trades" && (
          <div className="space-y-2">
            {filteredTrades.length === 0 ? (
              <div className="text-center py-12 text-[var(--text-dim)] text-sm">No trades match your filters</div>
            ) : (
              filteredTrades.map((t) => <TradeCard key={t.ticker} t={t} />)
            )}
          </div>
        )}

        {tab === "notrade" && (
          <div className="space-y-1.5">
            {filteredNoTrades.length === 0 ? (
              <div className="text-center py-12 text-[var(--text-dim)] text-sm">No items match your filters</div>
            ) : (
              filteredNoTrades.map((t) => <NoTradeRow key={t.ticker} t={t} />)
            )}
          </div>
        )}

        {/* Footer */}
        <div className="text-xs text-[var(--text-dim)] border-t border-[var(--border)] pt-4 flex flex-wrap gap-4">
          <span>Data: Polygon.io (5-year lookback)</span>
          <span>Engine: Orchestrator CWAF (TA + FA fusion)</span>
          <span>Run: {new Date(run_meta.run_date).toLocaleString()}</span>
          <span>Elapsed: {run_meta.elapsed_sec}s for {run_meta.total} tickers</span>
        </div>
      </div>
    </div>
  );
}
