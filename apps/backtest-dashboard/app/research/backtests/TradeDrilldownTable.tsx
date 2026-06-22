"use client";

import type { TickerDrilldownRow } from "@/app/lib/confusionBucket";

function fmtPrice(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(2);
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return "—";
  return String(v).slice(0, 10);
}

function displayTarget(t: TickerDrilldownRow): { text: string; title?: string } {
  if (t.targetT1 != null) {
    return { text: fmtPrice(t.targetT1), title: "Phoenix target 1" };
  }
  if (t.backtestTargetPrice != null) {
    return {
      text: fmtPrice(t.backtestTargetPrice),
      title: "Backtest label target (+5% from entry)",
    };
  }
  if (t.targetPrice != null) {
    return { text: fmtPrice(t.targetPrice) };
  }
  return { text: "—" };
}

function displayExitDate(t: TickerDrilldownRow): { text: string; title?: string } {
  if (t.targetHit === true && t.targetHitDate) {
    return { text: fmtDate(t.targetHitDate), title: "Date backtest target was first hit" };
  }
  if (t.exitReferenceDate) {
    return { text: fmtDate(t.exitReferenceDate), title: "End of eval window (reference exit)" };
  }
  return { text: "—" };
}

export function TradeDrilldownTable({
  rows,
  showTradeColumns = true,
}: {
  rows: TickerDrilldownRow[];
  /** When false, show the compact legacy columns only. */
  showTradeColumns?: boolean;
}) {
  if (rows.length === 0) return null;

  return (
    <div className="overflow-x-auto border border-current/20 rounded-lg max-h-80 mt-2">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-current/20 opacity-80">
            <th className="p-2 text-left">Ticker</th>
            <th className="p-2 text-left">Signal</th>
            {showTradeColumns && (
              <>
                <th className="p-2 text-left" title="Signal date — entry assumed at as-of close">
                  Entry date
                </th>
                <th className="p-2 text-right">Entry</th>
                <th className="p-2 text-right">Stop</th>
                <th className="p-2 text-right">Target</th>
                <th className="p-2 text-left">Exit date</th>
                <th className="p-2 text-right">Exit</th>
              </>
            )}
            <th className="p-2 text-center">Hit</th>
            <th className="p-2 text-left">Phoenix</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const target = displayTarget(t);
            const exitDate = displayExitDate(t);
            return (
              <tr key={t.ticker} className="border-b border-current/10 hover:bg-black/10">
                <td className="p-2 font-mono font-semibold">{t.ticker}</td>
                <td className="p-2">{t.signal}</td>
                {showTradeColumns && (
                  <>
                    <td className="p-2 font-mono tabular-nums">{fmtDate(t.entryDate)}</td>
                    <td className="p-2 text-right font-mono tabular-nums">{fmtPrice(t.entryPrice)}</td>
                    <td
                      className="p-2 text-right font-mono tabular-nums text-[var(--text-dim)]"
                      title={
                        t.stopPrice == null
                          ? "No Phoenix stop (recovery upgrade or hard-filter exit before risk calc)"
                          : undefined
                      }
                    >
                      {fmtPrice(t.stopPrice)}
                    </td>
                    <td className="p-2 text-right font-mono tabular-nums" title={target.title}>
                      {target.text}
                    </td>
                    <td className="p-2 font-mono tabular-nums" title={exitDate.title}>
                      {exitDate.text}
                    </td>
                    <td className="p-2 text-right font-mono tabular-nums">{fmtPrice(t.exitPrice)}</td>
                  </>
                )}
                <td className="p-2 text-center">
                  {t.targetHit === true ? "✓" : t.targetHit === false ? "✗" : "—"}
                </td>
                <td className="p-2 opacity-80">{t.phoenixDisplay || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function tradeDrilldownFootnote(showTradeColumns: boolean): string {
  if (!showTradeColumns) {
    return "Click TP / FP / TN / FN counts to list tickers.";
  }
  return (
    "Entry date = signal date (as-of close). Stop/target from Phoenix when available; " +
    "otherwise backtest +5% label target. Exit date = first target-hit day when hit, " +
    "else end of eval window."
  );
}
