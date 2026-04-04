"use client";

import { useMemo, useState } from "react";
import type { Signal, PredictionData, Prediction } from "../lib/types";
import { winRate, avgReturn, sharpeRatio, maxDrawdown, profitFactor } from "../lib/data-utils";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell,
  Legend,
} from "recharts";
import { ArrowUpRight, ArrowDownRight, Minus, TrendingUp, TrendingDown, Target } from "lucide-react";

interface Props {
  ticker: string;
  signals: Signal[];
  predictions: PredictionData;
  tickers: string[];
  onTickerChange: (t: string) => void;
}

function StatMini({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-[var(--text-dim)] uppercase tracking-wider">{label}</span>
      <span className={`text-lg font-bold font-mono ${color || ""}`}>{value}</span>
    </div>
  );
}

export default function StockDetail({ ticker, signals, predictions, tickers, onTickerChange }: Props) {
  const [agentFilter, setAgentFilter] = useState<string>("all");

  const tickerSignals = useMemo(
    () => signals.filter((s) => s.ticker === ticker),
    [signals, ticker]
  );

  const filteredSignals = useMemo(
    () =>
      agentFilter === "all"
        ? tickerSignals
        : tickerSignals.filter((s) => s.agent === agentFilter),
    [tickerSignals, agentFilter]
  );

  const agents = useMemo(
    () => [...new Set(tickerSignals.map((s) => s.agent))],
    [tickerSignals]
  );

  const prediction = predictions.predictions.find((p) => p.ticker === ticker);
  const sector = tickerSignals[0]?.sector || prediction?.sector || "Unknown";

  // Monthly performance chart data
  const monthlyData = useMemo(() => {
    const months = [...new Set(filteredSignals.map((s) => s.month))].sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime()
    );
    return months.map((m) => {
      const monthSignals = filteredSignals.filter((s) => s.month === m);
      const agents: Record<string, { signal: string; returnPct: number; correct: boolean | null; score: number | null }> = {};
      monthSignals.forEach((s) => {
        agents[s.agent] = {
          signal: s.signal,
          returnPct: s.returnPct,
          correct: s.correct,
          score: s.score,
        };
      });
      return {
        month: new Date(m + " 1").toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
        rawMonth: m,
        ...Object.fromEntries(
          monthSignals.map((s) => [`${s.agent}_return`, s.returnPct])
        ),
        ...Object.fromEntries(
          monthSignals.map((s) => [`${s.agent}_score`, s.score])
        ),
        returnPct: monthSignals[0]?.returnPct ?? 0,
        startPrice: monthSignals[0]?.startPrice,
        endPrice: monthSignals[0]?.endPrice,
      };
    });
  }, [filteredSignals]);

  // Entry/Exit price timeline
  const priceTimeline = useMemo(() => {
    return filteredSignals
      .sort((a, b) => new Date(a.signalDate).getTime() - new Date(b.signalDate).getTime())
      .map((s) => ({
        month: new Date(s.month + " 1").toLocaleDateString("en-US", { month: "short" }),
        entry: s.startPrice,
        exit: s.endPrice,
        signal: s.signal,
        correct: s.correct,
        agent: s.agent,
        target: s.targetPrice,
        stop: s.stopLoss,
      }));
  }, [filteredSignals]);

  // Framework radar data (from latest technical signals)
  const frameworkRadar = useMemo(() => {
    if (prediction?.techSubscores) {
      return Object.entries(prediction.techSubscores).map(([k, v]) => ({
        framework: k.replace(/_/g, " "),
        score: v ?? 0,
      }));
    }
    const techSignals = tickerSignals.filter((s) => s.agent === "technical" && s.frameworks);
    if (techSignals.length === 0) return [];
    const latest = techSignals[techSignals.length - 1];
    return Object.entries(latest.frameworks || {}).map(([k, v]) => ({
      framework: k.replace(/_/g, " "),
      score: v ?? 0,
    }));
  }, [tickerSignals, prediction]);

  // Score confidence scatter
  const scoreScatter = useMemo(() => {
    return filteredSignals
      .filter((s) => s.score !== null)
      .map((s) => ({
        score: s.score!,
        returnPct: s.returnPct,
        signal: s.signal,
        correct: s.correct,
        agent: s.agent,
        month: s.month,
      }));
  }, [filteredSignals]);

  // Stats
  const wr = winRate(filteredSignals);
  const avg = avgReturn(filteredSignals);
  const sharpe = sharpeRatio(filteredSignals);
  const mdd = maxDrawdown(filteredSignals);
  const pf = profitFactor(filteredSignals);
  const trades = filteredSignals.filter((s) => s.signal !== "HOLD").length;

  // Pattern identification from framework scores
  const patternSummary = useMemo(() => {
    if (!prediction?.techSubscores) return null;
    const scores = prediction.techSubscores;
    const patterns: string[] = [];

    if (scores.ema_trend >= 70) patterns.push("Strong EMA Trend");
    else if (scores.ema_trend <= 30) patterns.push("Weak EMA — Downtrend");

    if (scores.macd_system >= 70) patterns.push("MACD Bullish");
    else if (scores.macd_system <= 30) patterns.push("MACD Bearish Divergence");

    if (scores.rsi_regime >= 70) patterns.push("RSI Overbought Zone");
    else if (scores.rsi_regime <= 30) patterns.push("RSI Oversold Zone");
    else if (scores.rsi_regime >= 45 && scores.rsi_regime <= 55)
      patterns.push("RSI Neutral");

    if (scores.bollinger >= 70) patterns.push("Bollinger Squeeze Breakout");
    else if (scores.bollinger <= 30) patterns.push("Bollinger Band Rejection");

    if (scores.volume_obv >= 70) patterns.push("OBV Confirmation");
    else if (scores.volume_obv <= 30) patterns.push("OBV Divergence Warning");

    if (scores.pattern_recognition >= 70) patterns.push("Pattern: Bullish Formation");
    else if (scores.pattern_recognition <= 30) patterns.push("Pattern: Bearish Formation");

    if (scores.ichimoku >= 70) patterns.push("Above Ichimoku Cloud");
    else if (scores.ichimoku <= 30) patterns.push("Below Ichimoku Cloud");

    if (scores.momentum >= 70) patterns.push("Strong Momentum");
    else if (scores.momentum <= 30) patterns.push("Momentum Fading");

    return patterns;
  }, [prediction]);

  const signalColors: Record<string, string> = { BUY: "#22c55e", SELL: "#ef4444", HOLD: "#eab308" };

  return (
    <div className="space-y-6">
      {/* Header + Ticker selector */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <select
            value={ticker}
            onChange={(e) => onTickerChange(e.target.value)}
            className="text-xl font-bold font-mono bg-transparent border border-[var(--border)] rounded-lg px-3 py-1.5 text-[var(--text)]"
          >
            {tickers.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <span className="text-sm text-[var(--text-dim)] bg-[var(--bg-card)] px-3 py-1 rounded-full border border-[var(--border)]">
            {sector.replace("_", " ")}
          </span>
          {prediction && (
            <span
              className={`text-sm px-3 py-1 rounded-full font-semibold ${
                prediction.signalLabel === "BUY"
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : prediction.signalLabel === "SELL"
                  ? "bg-red-500/20 text-red-400 border border-red-500/30"
                  : "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
              }`}
            >
              {prediction.signalLabel === "BUY" && <ArrowUpRight size={14} className="inline mr-1" />}
              {prediction.signalLabel === "SELL" && <ArrowDownRight size={14} className="inline mr-1" />}
              {prediction.signalLabel === "HOLD" && <Minus size={14} className="inline mr-1" />}
              {prediction.signalLabel} — Score {prediction.orchestratorScore.toFixed(0)}
            </span>
          )}
        </div>

        {/* Agent filter */}
        <div className="flex gap-1">
          <button
            onClick={() => setAgentFilter("all")}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              agentFilter === "all"
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                : "text-[var(--text-dim)] hover:bg-white/5"
            }`}
          >
            All
          </button>
          {agents.map((a) => (
            <button
              key={a}
              onClick={() => setAgentFilter(a)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                agentFilter === a
                  ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                  : "text-[var(--text-dim)] hover:bg-white/5"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-4 p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
        <StatMini label="Win Rate" value={`${wr.toFixed(1)}%`} color={wr >= 55 ? "text-green-400" : wr >= 50 ? "text-yellow-400" : "text-red-400"} />
        <StatMini label="Avg Return" value={`${avg >= 0 ? "+" : ""}${avg.toFixed(2)}%`} color={avg >= 0 ? "text-green-400" : "text-red-400"} />
        <StatMini label="Sharpe" value={sharpe.toFixed(2)} color={sharpe >= 1 ? "text-green-400" : sharpe >= 0 ? "text-yellow-400" : "text-red-400"} />
        <StatMini label="Max DD" value={`${mdd.toFixed(1)}%`} color="text-red-400" />
        <StatMini label="Profit Factor" value={pf === Infinity ? "∞" : pf.toFixed(2)} color={pf >= 1.5 ? "text-green-400" : "text-yellow-400"} />
        <StatMini label="Trades" value={`${trades}`} />
      </div>

      {/* Row 1: Entry/Exit Price Chart + Monthly Returns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Entry/Exit Price */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            <Target size={14} className="inline mr-1.5" /> Entry / Exit Prices
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={priceTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(val: unknown, name: unknown) => [
                  `$${Number(val)?.toFixed(2)}`,
                  String(name) === "entry" ? "Entry Price" : String(name) === "exit" ? "Exit Price" : String(name) === "target" ? "Target" : "Stop Loss",
                ]}
              />
              <Legend />
              <Line type="monotone" dataKey="entry" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} name="Entry" />
              <Line type="monotone" dataKey="exit" stroke="#22c55e" strokeWidth={2} dot={{ r: 4 }} name="Exit" />
              {priceTimeline.some((p) => p.target) && (
                <Line type="monotone" dataKey="target" stroke="#3b82f6" strokeDasharray="5 5" dot={false} name="Target" />
              )}
              {priceTimeline.some((p) => p.stop) && (
                <Line type="monotone" dataKey="stop" stroke="#ef4444" strokeDasharray="5 5" dot={false} name="Stop" />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly Returns */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            <TrendingUp size={14} className="inline mr-1.5" /> Monthly Returns (%)
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <ReferenceLine y={0} stroke="#444" />
              <Bar dataKey="returnPct" name="Return %" radius={[4, 4, 0, 0]}>
                {monthlyData.map((entry, idx) => (
                  <Cell
                    key={idx}
                    fill={
                      (entry.returnPct as number) >= 0 ? "#22c55e" : "#ef4444"
                    }
                    fillOpacity={0.7}
                  />
                ))}
              </Bar>
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Framework Radar + Score vs Return Scatter */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pattern / Framework Radar */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            Framework Radar — Pattern Analysis
          </h3>
          {frameworkRadar.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={frameworkRadar}>
                  <PolarGrid stroke="#2a2a3a" />
                  <PolarAngleAxis dataKey="framework" tick={{ fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
                  <Radar
                    dataKey="score"
                    fill="#6366f1"
                    fillOpacity={0.3}
                    stroke="#6366f1"
                    strokeWidth={2}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#1a1a24",
                      border: "1px solid #2a2a3a",
                      borderRadius: 8,
                      fontSize: 11,
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>

              {/* Pattern Tags */}
              {patternSummary && patternSummary.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {patternSummary.map((p, i) => {
                    const isBullish = p.includes("Bullish") || p.includes("Strong") || p.includes("Above") || p.includes("Confirmation") || p.includes("Breakout");
                    const isBearish = p.includes("Bearish") || p.includes("Weak") || p.includes("Below") || p.includes("Divergence") || p.includes("Rejection") || p.includes("Fading") || p.includes("Overbought");
                    return (
                      <span
                        key={i}
                        className={`text-[10px] px-2 py-1 rounded-full border font-medium ${
                          isBullish
                            ? "bg-green-500/10 text-green-400 border-green-500/30"
                            : isBearish
                            ? "bg-red-500/10 text-red-400 border-red-500/30"
                            : "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
                        }`}
                      >
                        {p}
                      </span>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-[var(--text-dim)]">No framework data available.</p>
          )}
        </div>

        {/* Score vs Return Scatter */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
            Score vs Actual Return
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis type="number" dataKey="score" name="Score" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis type="number" dataKey="returnPct" name="Return %" tick={{ fontSize: 11 }} />
              <ZAxis range={[40, 40]} />
              <Tooltip
                contentStyle={{
                  background: "#1a1a24",
                  border: "1px solid #2a2a3a",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(val: unknown, name: unknown) => [
                  String(name) === "Score" ? Number(val).toFixed(1) : `${Number(val).toFixed(2)}%`,
                  String(name),
                ]}
              />
              <ReferenceLine y={0} stroke="#444" />
              <ReferenceLine x={50} stroke="#444" strokeDasharray="3 3" />
              <Scatter data={scoreScatter} name="Signals">
                {scoreScatter.map((d, i) => (
                  <Cell
                    key={i}
                    fill={signalColors[d.signal] || "#6366f1"}
                    fillOpacity={d.correct ? 0.8 : 0.3}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-4 mt-2 text-xs text-[var(--text-dim)]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" /> BUY
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" /> SELL
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-500" /> HOLD
            </span>
            <span>Bright = correct · Dim = incorrect</span>
          </div>
        </div>
      </div>

      {/* Row 3: Signal Log Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
        <h3 className="text-sm font-semibold text-[var(--text-dim)] uppercase tracking-wider mb-4">
          Signal History
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[var(--text-dim)] border-b border-[var(--border)]">
                <th className="px-3 py-2 text-left text-xs">Month</th>
                <th className="px-3 py-2 text-left text-xs">Agent</th>
                <th className="px-3 py-2 text-left text-xs">Signal</th>
                <th className="px-3 py-2 text-left text-xs">Trend</th>
                <th className="px-3 py-2 text-right text-xs">Entry</th>
                <th className="px-3 py-2 text-right text-xs">Target</th>
                <th className="px-3 py-2 text-right text-xs">Stop</th>
                <th className="px-3 py-2 text-right text-xs">Exit</th>
                <th className="px-3 py-2 text-right text-xs">Return</th>
                <th className="px-3 py-2 text-center text-xs">Days</th>
                <th className="px-3 py-2 text-left text-xs">Score</th>
                <th className="px-3 py-2 text-left text-xs">Patterns</th>
                <th className="px-3 py-2 text-center text-xs">Result</th>
              </tr>
            </thead>
            <tbody>
              {filteredSignals
                .sort((a, b) => new Date(b.signalDate).getTime() - new Date(a.signalDate).getTime())
                .map((s, i) => (
                  <tr key={i} className="border-b border-[var(--border)]/30 hover:bg-white/3">
                    <td className="px-3 py-2 text-xs text-[var(--text-dim)]">
                      {new Date(s.month + " 1").toLocaleDateString("en-US", {
                        month: "short",
                        year: "2-digit",
                      })}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded ${
                          s.agent === "technical"
                            ? "bg-indigo-500/20 text-indigo-400"
                            : s.agent === "fundamental"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-purple-500/20 text-purple-400"
                        }`}
                      >
                        {s.agent.slice(0, 4)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`text-xs font-semibold ${
                          s.signal === "BUY"
                            ? "text-green-400"
                            : s.signal === "SELL"
                            ? "text-red-400"
                            : "text-yellow-400"
                        }`}
                      >
                        {s.signal}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          s.rawSignal === "bullish"
                            ? "bg-green-500/15 text-green-400"
                            : s.rawSignal === "bearish"
                            ? "bg-red-500/15 text-red-400"
                            : "bg-yellow-500/15 text-yellow-400"
                        }`}
                      >
                        {s.rawSignal}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs">
                      ${s.startPrice.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs">
                      {s.targetPrice ? (
                        <span className="text-blue-400">${s.targetPrice.toFixed(2)}</span>
                      ) : (
                        <span className="text-[var(--text-dim)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs">
                      {s.stopLoss ? (
                        <span className="text-red-400">${s.stopLoss.toFixed(2)}</span>
                      ) : (
                        <span className="text-[var(--text-dim)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs">
                      ${s.endPrice.toFixed(2)}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono text-xs font-medium ${
                        s.returnPct >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {s.returnPct >= 0 ? "+" : ""}
                      {s.returnPct.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 text-center font-mono text-xs text-[var(--text-dim)]">
                      {s.tradeDurationDays ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {s.score !== null ? s.score.toFixed(0) : "—"}
                      {s.scoreBand && (
                        <span className="ml-1 text-[10px] text-[var(--text-dim)]">{s.scoreBand}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs max-w-[160px]">
                      {s.patterns && s.patterns.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {s.patterns.slice(0, 2).map((p, pi) => (
                            <span
                              key={pi}
                              className={`text-[10px] px-1.5 py-0.5 rounded ${
                                p.direction === "bullish"
                                  ? "bg-green-500/15 text-green-400"
                                  : p.direction === "bearish"
                                  ? "bg-red-500/15 text-red-400"
                                  : "bg-gray-500/15 text-gray-400"
                              }`}
                              title={`${p.name} (${(p.confidence * 100).toFixed(0)}%)`}
                            >
                              {p.name}
                            </span>
                          ))}
                          {s.patterns.length > 2 && (
                            <span className="text-[10px] text-[var(--text-dim)]">
                              +{s.patterns.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[var(--text-dim)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {s.correct === null ? (
                        <span className="text-xs text-[var(--text-dim)]">—</span>
                      ) : s.correct ? (
                        <span className="text-xs text-green-400">✓</span>
                      ) : (
                        <span className="text-xs text-red-400">✗</span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Prediction Detail */}
      {prediction && (
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-5">
          <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-4">
            Live Prediction — {prediction.date}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 text-xs">
            <div>
              <span className="text-[var(--text-dim)]">Signal</span>
              <p className="font-bold text-lg">{prediction.signalLabel}</p>
            </div>
            <div>
              <span className="text-[var(--text-dim)]">Score</span>
              <p className="font-bold text-lg font-mono">{prediction.orchestratorScore.toFixed(1)}</p>
            </div>
            <div>
              <span className="text-[var(--text-dim)]">Confidence</span>
              <p className="font-bold text-lg font-mono">{(prediction.confidence * 100).toFixed(0)}%</p>
            </div>
            <div>
              <span className="text-[var(--text-dim)]">Tech</span>
              <p className="font-bold text-lg font-mono">
                {prediction.techScore?.toFixed(1) ?? "—"}{" "}
                <span className="text-[10px] text-[var(--text-dim)]">{prediction.techBand}</span>
              </p>
            </div>
            <div>
              <span className="text-[var(--text-dim)]">Fund</span>
              <p className="font-bold text-lg font-mono">
                {prediction.fundScore?.toFixed(1) ?? "—"}{" "}
                <span className="text-[10px] text-[var(--text-dim)]">{prediction.fundBand}</span>
              </p>
            </div>
            <div>
              <span className="text-[var(--text-dim)]">Weights</span>
              <p className="font-bold text-lg font-mono">
                {(prediction.weightTech * 100).toFixed(0)}/{(prediction.weightFund * 100).toFixed(0)}
              </p>
            </div>
          </div>
          {prediction.conflictDetected && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-orange-500/10 border border-orange-500/30 text-xs text-orange-400">
              ⚠ Conflict detected — Resolution: {prediction.conflictResolution || "N/A"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
