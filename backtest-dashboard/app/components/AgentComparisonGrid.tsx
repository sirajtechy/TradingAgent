"use client";

import { AgentSummary } from "@/app/lib/types";

interface Props {
  summaries: AgentSummary[];
}

const agentColors: Record<string, string> = {
  technical: "border-blue-500/30 from-blue-500/10",
  fundamental: "border-emerald-500/30 from-emerald-500/10",
  orchestrator: "border-purple-500/30 from-purple-500/10",
};

const textColors: Record<string, string> = {
  technical: "text-blue-400",
  fundamental: "text-emerald-400",
  orchestrator: "text-purple-400",
};

export default function AgentComparisonGrid({ summaries }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {summaries.map((s) => {
        const winRate = s.winRate ?? 0;
        const abstention = s.totalPeriods ? ((s.holds / s.totalPeriods) * 100).toFixed(1) : "0";
        const tp = s.cm.buyUp;
        const fp = s.cm.buyDown;
        const fn = s.cm.sellUp;
        const tn = s.cm.sellDown;
        const directional = tp + fp + fn + tn;
        const precision = (tp + fp) ? ((tp / (tp + fp)) * 100).toFixed(1) : "—";
        const recall = (tp + fn) ? ((tp / (tp + fn)) * 100).toFixed(1) : "—";

        return (
          <div
            key={s.agent}
            className={`bg-gradient-to-br ${agentColors[s.agent]} to-transparent border rounded-xl p-5`}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className={`text-lg font-bold capitalize ${textColors[s.agent]}`}>{s.agent}</h3>
              <span className="text-xs text-gray-500">{s.tickers.length} tickers</span>
            </div>

            <div className="space-y-3">
              {/* Win rate */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">Win Rate</span>
                  <span className={`font-bold ${winRate >= 55 ? "text-emerald-400" : winRate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                    {winRate.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500"
                    style={{ width: `${winRate}%` }}
                  />
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-800/30 rounded-lg px-3 py-2">
                  <p className="text-gray-500">Trades</p>
                  <p className="font-bold text-gray-200">{s.totalTrades}</p>
                </div>
                <div className="bg-gray-800/30 rounded-lg px-3 py-2">
                  <p className="text-gray-500">Abstention</p>
                  <p className="font-bold text-gray-200">{abstention}%</p>
                </div>
                <div className="bg-gray-800/30 rounded-lg px-3 py-2">
                  <p className="text-gray-500">Precision</p>
                  <p className="font-bold text-gray-200">{precision}%</p>
                </div>
                <div className="bg-gray-800/30 rounded-lg px-3 py-2">
                  <p className="text-gray-500">Recall</p>
                  <p className="font-bold text-gray-200">{recall}%</p>
                </div>
              </div>

              {/* Signal distribution */}
              <div className="flex gap-1 h-4 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500/70"
                  style={{ width: `${(s.buys / s.totalPeriods) * 100}%` }}
                  title={`BUY: ${s.buys}`}
                />
                <div
                  className="bg-red-500/70"
                  style={{ width: `${(s.sells / s.totalPeriods) * 100}%` }}
                  title={`SELL: ${s.sells}`}
                />
                <div
                  className="bg-gray-500/70"
                  style={{ width: `${(s.holds / s.totalPeriods) * 100}%` }}
                  title={`HOLD: ${s.holds}`}
                />
              </div>
              <div className="flex justify-between text-[10px] text-gray-500">
                <span>BUY: {s.buys}</span>
                <span>SELL: {s.sells}</span>
                <span>HOLD: {s.holds}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
