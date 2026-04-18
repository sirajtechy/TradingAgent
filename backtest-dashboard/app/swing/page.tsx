"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  BarChart2,
  Layers,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface PatternTrigger {
  name: string;
  direction: string;
  confidence: number;
  breakout_confirmed: boolean;
  volume_confirmed: boolean;
  breakout_price: number | null;
  pattern_target: number | null;
  start_date: string | null;
  end_date: string | null;
  description: string;
}

interface TradeSetup {
  direction: "BULLISH" | "BEARISH";
  entry_date: string;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  exit_date_est: string;
  holding_days_est: number;
  daily_score: number;
  daily_band: string;
  confidence_band: "high" | "medium" | "low";
  boosted_confidence_pct: number;
  profit_probability: number;
  expected_profit_pct: number;
  risk_pct: number;
  reward_risk_ratio: number;
  atr_at_entry: number;
  adx_at_entry: number | null;
  rsi_at_entry: number | null;
  weekly_signal: string | null;
  weekly_band: string | null;
  timeframe_alignment: string;
  pattern_triggers: PatternTrigger[];
  aligned_pattern_count: number;
  weekly_pattern_triggers: PatternTrigger[];
}

interface ActualOutcome {
  end_price: number;
  actual_exit_price: number;
  actual_exit_date: string;
  actual_date: string;
  price_return_pct: number;
  actual_direction: string;
  predicted_direction: string;
  signal_correct: boolean;
}

interface Period {
  period: string;
  signal_date: string;
  result_date: string;
  is_current: boolean;
  trade_setup: TradeSetup | null;
  actual_outcome: ActualOutcome | null;
  no_trade_reason: string | null;
  error: string | null;
}

interface TickerSummary {
  total_periods: number;
  swing_trades_generated: number;
  completed_trades: number;
  n_correct: number;
  accuracy_pct: number | null;
  bullish_trades: number;
  bearish_trades: number;
  error_periods: number;
}

interface TickerData {
  ticker: string;
  cap_tier: string;
  sector: string;
  periods: Period[];
  ticker_summary: TickerSummary;
  current_setup: TradeSetup | null;
}

interface MatrixCell {
  TP: number; FP: number; FN: number; TN: number;
  total_evaluated: number;
  accuracy_pct: number | null;
  precision_pct: number | null;
  recall_pct: number | null;
  f1_score: number | null;
  MCC: number | null;
}

interface ConfusionMatrix {
  overall: MatrixCell;
  by_confidence: Record<string, MatrixCell>;
  by_alignment: Record<string, MatrixCell>;
  meta: { no_trade_periods: number; pending_periods: number; note: string };
}

interface TradeCandidate extends TradeSetup {
  ticker: string;
  cap_tier: string;
  sector: string;
}

interface BacktestData {
  meta: {
    run_timestamp: string;
    cutoff_date: string;
    first_signal_date: string;
    current_signal_date: string;
    tickers: string[];
    signal_windows: { signal_date: string; result_date: string }[];
    swing_min_days: number;
    swing_max_days: number;
    data_source: string;
  };
  aggregate_summary: {
    total_tickers: number;
    total_periods_run: number;
    total_swing_trades: number;
    total_completed_trades: number;
    overall_accuracy_pct: number | null;
    trade_candidates_today: number;
  };
  confusion_matrix: ConfusionMatrix;
  trade_candidates: TradeCandidate[];
  tickers: Record<string, TickerData>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Small display components
// ─────────────────────────────────────────────────────────────────────────────

function DirectionBadge({ d }: { d: string }) {
  const bull = d === "BULLISH";
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full border
        ${bull
          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
          : "bg-red-500/15 text-red-400 border-red-500/30"
        }`}
    >
      {bull ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {d}
    </span>
  );
}

function ConfBadge({ band }: { band: string }) {
  const cls =
    band === "high"
      ? "bg-sky-500/15 text-sky-400 border-sky-500/30"
      : band === "medium"
      ? "bg-yellow-500/15 text-yellow-400 border-yellow-500/30"
      : "bg-slate-500/15 text-slate-400 border-slate-500/30";
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border uppercase tracking-wide ${cls}`}>
      {band}
    </span>
  );
}

function AlignBadge({ a }: { a: string }) {
  const label = a === "aligned" ? "TF aligned" : a === "conflict" ? "TF conflict" : a === "weekly_neutral" ? "weekly n/a" : "daily only";
  const cls =
    a === "aligned"
      ? "text-emerald-400"
      : a === "conflict"
      ? "text-red-400"
      : "text-slate-400";
  return <span className={`text-[10px] ${cls}`}>{label}</span>;
}

function OutcomeBadge({ ao }: { ao: ActualOutcome }) {
  if (ao.signal_correct) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400">
        <CheckCircle size={13} /> CORRECT
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-bold text-red-400">
      <XCircle size={13} /> WRONG
    </span>
  );
}

function AccBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-xs text-slate-500">n/a</span>;
  const color = pct >= 60 ? "bg-emerald-500" : pct >= 45 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-semibold">{pct.toFixed(1)}%</span>
    </div>
  );
}

function MatrixBox({ cell, label }: { cell: MatrixCell; label: string }) {
  if (!cell.total_evaluated) return null;
  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10 space-y-3">
      <div className="text-xs font-bold text-slate-300 uppercase tracking-wider">{label}</div>
      <div className="grid grid-cols-2 gap-1 text-center text-xs font-mono">
        <div className="text-slate-400 col-span-2 text-[10px] mb-1">
          ← actual UP &nbsp;&nbsp;&nbsp;&nbsp; actual DOWN →
        </div>
        <div className="bg-emerald-500/15 border border-emerald-500/20 rounded p-2">
          <div className="text-emerald-400 font-bold text-base">{cell.TP}</div>
          <div className="text-[10px] text-slate-400">BULL TP</div>
        </div>
        <div className="bg-red-500/15 border border-red-500/20 rounded p-2">
          <div className="text-red-400 font-bold text-base">{cell.FP}</div>
          <div className="text-[10px] text-slate-400">BULL FP</div>
        </div>
        <div className="bg-orange-500/15 border border-orange-500/20 rounded p-2">
          <div className="text-orange-400 font-bold text-base">{cell.FN}</div>
          <div className="text-[10px] text-slate-400">BEAR FN</div>
        </div>
        <div className="bg-emerald-500/15 border border-emerald-500/20 rounded p-2">
          <div className="text-emerald-400 font-bold text-base">{cell.TN}</div>
          <div className="text-[10px] text-slate-400">BEAR TN</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <div className="flex justify-between"><span className="text-slate-400">Accuracy</span><span className="font-mono font-semibold">{cell.accuracy_pct ?? "–"}%</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Precision</span><span className="font-mono font-semibold">{cell.precision_pct ?? "–"}%</span></div>
        <div className="flex justify-between"><span className="text-slate-400">Recall</span><span className="font-mono font-semibold">{cell.recall_pct ?? "–"}%</span></div>
        <div className="flex justify-between"><span className="text-slate-400">F1</span><span className="font-mono font-semibold">{cell.f1_score ?? "–"}</span></div>
        <div className="flex justify-between col-span-2"><span className="text-slate-400">MCC (ideal=1)</span><span className="font-mono font-semibold">{cell.MCC ?? "–"}</span></div>
        <div className="flex justify-between col-span-2 text-slate-500 pt-1 border-t border-white/10">
          <span>n</span><span className="font-mono">{cell.total_evaluated} trades</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function SwingBacktestPage() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "trades" | "matrix" | "forward">("overview");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/swing-backtest", { cache: "no-store" });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // ── flatten all completed historical trades ───────────────────────────────
  const completedTrades: Array<{ ticker: string; cap_tier: string; sector: string; period: Period }> = [];
  if (data) {
    for (const [ticker, td] of Object.entries(data.tickers)) {
      for (const p of td.periods) {
        if (!p.is_current && p.trade_setup && p.actual_outcome && "signal_correct" in p.actual_outcome) {
          completedTrades.push({ ticker, cap_tier: td.cap_tier, sector: td.sector, period: p });
        }
      }
    }
    completedTrades.sort((a, b) => a.period.signal_date.localeCompare(b.period.signal_date));
  }

  // ─────────────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
      <div className="text-slate-400 flex items-center gap-2"><RefreshCw size={18} className="animate-spin" /> Loading swing backtest…</div>
    </div>
  );

  if (error || !data) return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
      <div className="text-center space-y-3">
        <AlertCircle size={32} className="text-red-400 mx-auto" />
        <p className="text-red-400 font-semibold">{error ?? "No data"}</p>
        <p className="text-slate-500 text-sm">Run the backtest script first:<br /><code className="text-slate-300">python scripts/backtests/run_swing_backtest_jan2026.py</code></p>
        <button onClick={load} className="mt-2 px-4 py-2 bg-white/10 rounded-lg text-sm text-slate-300 hover:bg-white/15">
          Retry
        </button>
      </div>
    </div>
  );

  const agg = data.aggregate_summary;
  const cm = data.confusion_matrix;
  const ov = cm?.overall;

  const tabs: { key: typeof activeTab; label: string; icon: React.ReactNode }[] = [
    { key: "overview",  label: "Overview",        icon: <BarChart2 size={14} /> },
    { key: "trades",    label: "Trade Log",        icon: <Layers size={14} /> },
    { key: "matrix",    label: "Confusion Matrix", icon: <BarChart2 size={14} /> },
    { key: "forward",   label: "Live Picks",       icon: <TrendingUp size={14} /> },
  ];

  return (
    <div className="min-h-screen bg-[#0d1117] text-slate-100 font-sans">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="border-b border-white/10 bg-[#0d1117]/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold tracking-tight">Swing Backtest — Jan 2026</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Cutoff {data.meta.cutoff_date} · Polygon.io only · Swing {data.meta.swing_min_days}–{data.meta.swing_max_days}d
              · Generated {new Date(data.meta.run_timestamp).toLocaleString()}
            </p>
          </div>
          <button onClick={load} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/20 transition-colors">
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
        {/* Tabs */}
        <div className="max-w-6xl mx-auto px-6 flex gap-1 pb-0">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-1.5 text-xs px-4 py-2.5 border-b-2 transition-colors font-medium
                ${activeTab === t.key
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-slate-500 hover:text-slate-300"}`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">

        {/* ══ OVERVIEW TAB ══════════════════════════════════════════════════════ */}
        {activeTab === "overview" && (
          <>
            {/* KPI strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Tickers tested",    value: agg.total_tickers,                  sub: data.meta.tickers.join(", ") },
                { label: "Swing trades found", value: agg.total_swing_trades,             sub: `${agg.total_completed_trades} completed, ${agg.total_swing_trades - agg.total_completed_trades} open` },
                { label: "Overall accuracy",   value: agg.overall_accuracy_pct != null ? `${agg.overall_accuracy_pct}%` : "–", sub: `${agg.total_completed_trades} evaluated trades` },
                { label: "Live picks today",   value: agg.trade_candidates_today,          sub: `signal date ${data.meta.current_signal_date}` },
              ].map(k => (
                <div key={k.label} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="text-xl font-bold font-mono">{k.value}</div>
                  <div className="text-xs font-semibold text-slate-300 mt-0.5">{k.label}</div>
                  <div className="text-[10px] text-slate-500 mt-1">{k.sub}</div>
                </div>
              ))}
            </div>

            {/* Ticker accuracy table */}
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-white/10">
                <h2 className="text-sm font-bold">Ticker Performance — Historical Windows</h2>
                <p className="text-[11px] text-slate-500 mt-0.5">Click a row to expand full period detail</p>
              </div>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-white/10">
                    <th className="px-5 py-2 font-medium">Ticker</th>
                    <th className="px-3 py-2 font-medium">Cap</th>
                    <th className="px-3 py-2 font-medium">Sector</th>
                    <th className="px-3 py-2 font-medium">Trades</th>
                    <th className="px-3 py-2 font-medium">Correct</th>
                    <th className="px-3 py-2 font-medium">Accuracy</th>
                    <th className="px-3 py-2 font-medium">Live Setup</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.tickers).map(([ticker, td]) => {
                    const ts = td.ticker_summary;
                    const isExpanded = expandedTicker === ticker;
                    const cs = td.current_setup;
                    return (
                      <>
                        <tr
                          key={ticker}
                          className="border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
                          onClick={() => setExpandedTicker(isExpanded ? null : ticker)}
                        >
                          <td className="px-5 py-3 font-semibold font-mono">{ticker}</td>
                          <td className="px-3 py-3">
                            <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded">{td.cap_tier}</span>
                          </td>
                          <td className="px-3 py-3 text-slate-400">{td.sector}</td>
                          <td className="px-3 py-3 font-mono">{ts.completed_trades}/{ts.swing_trades_generated}</td>
                          <td className="px-3 py-3 font-mono">{ts.n_correct}</td>
                          <td className="px-3 py-3"><AccBar pct={ts.accuracy_pct} /></td>
                          <td className="px-3 py-3">
                            {cs ? (
                              <div className="flex items-center gap-2">
                                <DirectionBadge d={cs.direction} />
                                <span className="text-slate-400 font-mono">${cs.entry_price}</span>
                                <span className="text-slate-600"><ArrowRight size={10} /></span>
                                <span className="text-slate-300 font-mono">${cs.target_price}</span>
                              </div>
                            ) : (
                              <span className="text-slate-600">no signal</span>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${ticker}-expand`} className="bg-white/3">
                            <td colSpan={7} className="px-5 py-4">
                              <div className="space-y-2">
                                {td.periods.map((p, i) => (
                                  <PeriodRow key={i} period={p} />
                                ))}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* ══ TRADE LOG TAB ═════════════════════════════════════════════════════ */}
        {activeTab === "trades" && (
          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10">
              <h2 className="text-sm font-bold">Complete Historical Trade Log</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">All swing trades with real entry → exit prices from Polygon. Jan–Mar 2026 only.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-white/10 bg-white/5">
                    <th className="px-4 py-2.5 font-medium">Ticker</th>
                    <th className="px-3 py-2.5 font-medium">Dir</th>
                    <th className="px-3 py-2.5 font-medium">Entry Date</th>
                    <th className="px-3 py-2.5 font-medium">Entry $</th>
                    <th className="px-3 py-2.5 font-medium">Exit Date</th>
                    <th className="px-3 py-2.5 font-medium">Exit $</th>
                    <th className="px-3 py-2.5 font-medium">Return</th>
                    <th className="px-3 py-2.5 font-medium">Target</th>
                    <th className="px-3 py-2.5 font-medium">Stop</th>
                    <th className="px-3 py-2.5 font-medium">Hold</th>
                    <th className="px-3 py-2.5 font-medium">Conf</th>
                    <th className="px-3 py-2.5 font-medium">Patterns</th>
                    <th className="px-3 py-2.5 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {completedTrades.map(({ ticker, period }, i) => {
                    const ts = period.trade_setup!;
                    const ao = period.actual_outcome!;
                    const pats = ts.pattern_triggers.filter(p => p.name && p.name !== "Unknown");
                    return (
                      <tr
                        key={i}
                        className={`border-b border-white/5 hover:bg-white/5 transition-colors
                          ${ao.signal_correct ? "border-l-2 border-l-emerald-500/40" : "border-l-2 border-l-red-500/40"}`}
                      >
                        <td className="px-4 py-3 font-mono font-semibold">{ticker}</td>
                        <td className="px-3 py-3"><DirectionBadge d={ts.direction} /></td>
                        <td className="px-3 py-3 text-slate-300 font-mono">{ts.entry_date}</td>
                        <td className="px-3 py-3 font-mono">${ts.entry_price.toFixed(2)}</td>
                        <td className="px-3 py-3 text-slate-300 font-mono">{ao.actual_exit_date}</td>
                        <td className="px-3 py-3 font-mono">${ao.actual_exit_price.toFixed(2)}</td>
                        <td className={`px-3 py-3 font-mono font-semibold ${ao.price_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {ao.price_return_pct >= 0 ? "+" : ""}{ao.price_return_pct.toFixed(2)}%
                        </td>
                        <td className="px-3 py-3 font-mono text-slate-400">${ts.target_price.toFixed(2)}</td>
                        <td className="px-3 py-3 font-mono text-slate-400">${ts.stop_loss.toFixed(2)}</td>
                        <td className="px-3 py-3 text-slate-400">{ts.holding_days_est}d</td>
                        <td className="px-3 py-3"><ConfBadge band={ts.confidence_band} /></td>
                        <td className="px-3 py-3">
                          {pats.length > 0 ? (
                            <div className="flex flex-col gap-0.5">
                              {pats.slice(0, 2).map((p, j) => (
                                <span key={j} className="text-[10px] text-sky-400">
                                  {p.breakout_confirmed && "✓ "}{p.name}
                                  <span className="text-slate-500 ml-1">({(p.confidence * 100).toFixed(0)}%)</span>
                                </span>
                              ))}
                              {pats.length > 2 && <span className="text-[10px] text-slate-500">+{pats.length - 2} more</span>}
                            </div>
                          ) : (
                            <span className="text-slate-600 text-[10px]">none detected</span>
                          )}
                        </td>
                        <td className="px-3 py-3"><OutcomeBadge ao={ao} /></td>
                      </tr>
                    );
                  })}
                  {completedTrades.length === 0 && (
                    <tr>
                      <td colSpan={13} className="text-center py-8 text-slate-500">No completed trades loaded</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ══ CONFUSION MATRIX TAB ══════════════════════════════════════════════ */}
        {activeTab === "matrix" && cm && (
          <div className="space-y-4">
            <div className="bg-white/5 border border-white/10 rounded-xl p-5">
              <h2 className="text-sm font-bold mb-1">How to read this</h2>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <strong className="text-slate-200">BULL TP</strong> = predicted BULLISH, stock went UP (correct) ·{" "}
                <strong className="text-slate-200">BULL FP</strong> = predicted BULLISH, went DOWN (wrong) ·{" "}
                <strong className="text-slate-200">BEAR FN</strong> = predicted BEARISH, went UP (wrong) ·{" "}
                <strong className="text-slate-200">BEAR TN</strong> = predicted BEARISH, went DOWN (correct).
                High MCC = strong signal. MCC near 0 = coin flip.
              </p>
              <p className="text-[11px] text-slate-500 mt-2">
                Sample size: {cm.overall.total_evaluated} completed trades ·
                Pending: {cm.meta.pending_periods} still open · Skipped (NEUTRAL): {cm.meta.no_trade_periods}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <MatrixBox cell={cm.overall} label="Overall" />
              <MatrixBox cell={cm.by_confidence?.high} label="Confidence: HIGH" />
              <MatrixBox cell={cm.by_confidence?.medium} label="Confidence: MEDIUM" />
              <MatrixBox cell={cm.by_alignment?.aligned} label="TF: Aligned (daily+weekly agree)" />
              <MatrixBox cell={cm.by_alignment?.weekly_neutral} label="TF: Weekly neutral (daily only)" />
              <MatrixBox cell={cm.by_alignment?.conflict} label="TF: Conflict (opposing signals)" />
            </div>
          </div>
        )}

        {/* ══ FORWARD / LIVE PICKS TAB ══════════════════════════════════════════ */}
        {activeTab === "forward" && (
          <div className="space-y-4">
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-5 py-3">
              <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                <AlertCircle size={15} />
                Forward predictions — no actual outcomes yet
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Signal date: <strong className="text-slate-200">{data.meta.current_signal_date}</strong>.
                These trades are still open. Entry prices are Polygon close prices as of signal date.
                Exit at estimated exit date — check Polygon for actual results.
              </p>
            </div>

            <div className="grid gap-4">
              {data.trade_candidates.map((cand, i) => {
                const pats = (cand.pattern_triggers || []).filter(p => p.name && p.name !== "Unknown");
                const wPats = (cand.weekly_pattern_triggers || []).filter(p => p.name && p.name !== "Unknown");
                return (
                  <div key={i} className={`bg-white/5 border rounded-xl p-5 space-y-4
                    ${cand.direction === "BULLISH" ? "border-emerald-500/20" : "border-red-500/20"}`}>

                    {/* Top row */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-xl font-bold font-mono">{cand.ticker}</span>
                        <span className="text-xs bg-white/10 px-2 py-0.5 rounded">{cand.cap_tier}</span>
                        <DirectionBadge d={cand.direction} />
                        <ConfBadge band={cand.confidence_band} />
                        <AlignBadge a={cand.timeframe_alignment} />
                      </div>
                      <div className="text-right">
                        <div className="text-[11px] text-slate-500">{cand.sector}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">ADX {cand.adx_at_entry?.toFixed(1) ?? "–"} · RSI {cand.rsi_at_entry?.toFixed(1) ?? "–"}</div>
                      </div>
                    </div>

                    {/* Price grid */}
                    <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                      {[
                        { l: "Entry Date",  v: cand.entry_date,     mono: false },
                        { l: "Entry Price", v: `$${cand.entry_price.toFixed(2)}`, mono: true },
                        { l: "Target",      v: `$${cand.target_price.toFixed(2)}`, mono: true, highlight: "text-emerald-400" },
                        { l: "Stop Loss",   v: `$${cand.stop_loss.toFixed(2)}`,    mono: true, highlight: "text-red-400" },
                        { l: "Est. Exit",   v: cand.exit_date_est,  mono: false },
                        { l: "Hold Est.",   v: `${cand.holding_days_est}d`,        mono: true },
                      ].map(f => (
                        <div key={f.l} className="bg-white/5 rounded-lg p-2.5">
                          <div className="text-[10px] text-slate-500">{f.l}</div>
                          <div className={`text-sm font-semibold mt-0.5 ${f.highlight ?? ""} ${f.mono ? "font-mono" : ""}`}>{f.v}</div>
                        </div>
                      ))}
                    </div>

                    {/* Risk/reward */}
                    <div className="flex flex-wrap gap-4 text-[11px]">
                      <div className="text-slate-400">Expected gain: <span className="text-emerald-400 font-semibold">{cand.expected_profit_pct}%</span></div>
                      <div className="text-slate-400">Risk: <span className="text-red-400 font-semibold">{cand.risk_pct}%</span></div>
                      <div className="text-slate-400">R/R: <span className="font-semibold text-slate-200">{cand.reward_risk_ratio}×</span></div>
                      <div className="text-slate-400">Score: <span className="font-mono font-semibold">{cand.daily_score}</span></div>
                      <div className="text-slate-400">Conviction: <span className="font-mono font-semibold">{cand.boosted_confidence_pct.toFixed(1)}%</span></div>
                      {cand.weekly_signal && <div className="text-slate-400">Weekly: <span className={`font-semibold ${cand.weekly_signal === "BULLISH" ? "text-emerald-400" : cand.weekly_signal === "BEARISH" ? "text-red-400" : "text-slate-400"}`}>{cand.weekly_signal}</span></div>}
                    </div>

                    {/* Patterns */}
                    {(pats.length > 0 || wPats.length > 0) && (
                      <div className="space-y-2">
                        {pats.length > 0 && (
                          <div>
                            <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1.5">Daily patterns</div>
                            <div className="flex flex-wrap gap-2">
                              {pats.map((p, j) => (
                                <div key={j} className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-[11px]">
                                  <span className={p.direction === "bullish" ? "text-emerald-400" : "text-red-400"}>
                                    {p.breakout_confirmed ? "✓ " : ""}{p.name}
                                  </span>
                                  <span className="text-slate-500 ml-1.5">{(p.confidence * 100).toFixed(0)}%</span>
                                  {p.pattern_target && (
                                    <span className="text-slate-500 ml-1.5">tgt ${p.pattern_target.toFixed(2)}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {wPats.length > 0 && (
                          <div>
                            <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1.5">Weekly patterns</div>
                            <div className="flex flex-wrap gap-2">
                              {wPats.map((p, j) => (
                                <div key={j} className="bg-white/5 border border-sky-500/20 rounded-lg px-3 py-1.5 text-[11px]">
                                  <span className="text-sky-400">{p.name}</span>
                                  <span className="text-slate-500 ml-1.5">{(p.confidence * 100).toFixed(0)}%</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {pats.length === 0 && wPats.length === 0 && (
                          <p className="text-[11px] text-slate-600">No patterns above confidence threshold</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PeriodRow — used in the expandable ticker detail
// ─────────────────────────────────────────────────────────────────────────────

function PeriodRow({ period }: { period: Period }) {
  const ts = period.trade_setup;
  const ao = period.actual_outcome;
  const isPending = period.is_current;

  if (!ts) {
    return (
      <div className="flex items-center gap-3 text-[11px] text-slate-500 pl-2">
        <Clock size={11} />
        <span className="font-mono text-slate-400">{period.signal_date}</span>
        <span>{period.no_trade_reason ?? period.error ?? "No trade"}</span>
      </div>
    );
  }

  const pats = ts.pattern_triggers.filter(p => p.name && p.name !== "Unknown");

  return (
    <div className={`rounded-lg border p-3 space-y-2 text-[11px]
      ${isPending ? "border-amber-500/20 bg-amber-500/5" : ao?.signal_correct ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"}`}>

      {/* Row 1: direction + price flow */}
      <div className="flex flex-wrap items-center gap-2">
        <DirectionBadge d={ts.direction} />
        <ConfBadge band={ts.confidence_band} />
        <AlignBadge a={ts.timeframe_alignment} />
        {isPending && <span className="text-[10px] text-amber-400 font-semibold">OPEN</span>}
      </div>

      {/* Row 2: entry → exit */}
      <div className="flex flex-wrap items-center gap-1.5 font-mono text-slate-300">
        <span className="text-slate-500">entry</span>
        <span className="font-semibold">{ts.entry_date}</span>
        <span className="text-slate-600">@</span>
        <span className="font-semibold">${ts.entry_price.toFixed(2)}</span>
        <ArrowRight size={10} className="text-slate-600" />
        <span className="text-slate-500">target</span>
        <span className="text-emerald-400 font-semibold">${ts.target_price.toFixed(2)}</span>
        <span className="text-slate-600 mx-1">|</span>
        <span className="text-slate-500">stop</span>
        <span className="text-red-400 font-semibold">${ts.stop_loss.toFixed(2)}</span>
        <span className="text-slate-600 mx-1">|</span>
        <span className="text-slate-500">est exit</span>
        <span className="font-semibold">{ts.exit_date_est}</span>
        <span className="text-slate-500 ml-1">({ts.holding_days_est}d)</span>
      </div>

      {/* Row 3: actual outcome */}
      {ao && "signal_correct" in ao && (
        <div className="flex flex-wrap items-center gap-2 font-mono">
          <OutcomeBadge ao={ao} />
          <span className="text-slate-500">actual exit</span>
          <span className="font-semibold">{ao.actual_exit_date}</span>
          <span className="text-slate-600">@</span>
          <span className="font-semibold">${ao.actual_exit_price.toFixed(2)}</span>
          <span className={`font-bold ml-1 ${ao.price_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {ao.price_return_pct >= 0 ? "+" : ""}{ao.price_return_pct.toFixed(2)}%
          </span>
        </div>
      )}

      {/* Row 4: patterns */}
      {pats.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {pats.map((p, i) => (
            <span key={i} className="bg-white/5 border border-sky-500/20 rounded px-2 py-0.5 text-[10px] text-sky-400">
              {p.breakout_confirmed ? "✓ " : ""}{p.name} {(p.confidence * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
