/**
 * Export dashboard signals to an Excel (.xlsx) workbook.
 * Uses the SheetJS library (xlsx).
 */
import * as XLSX from "xlsx";
import { Signal, AgentSummary, DashboardData, ConfusionMatrix } from "./types";

/* ── Flatten a signal row for the "Signals" sheet ────────── */

function signalRow(s: Signal) {
  return {
    Ticker: s.ticker,
    Sector: s.sector,
    Agent: s.agent,
    Month: s.month,
    "Signal Date": s.signalDate,
    "Result Date": s.resultDate,
    "Start Price": s.startPrice,
    "End Price": s.endPrice,
    "Return %": s.returnPct,
    Direction: s.actualDirection,
    Signal: s.signal,
    "Raw Signal": s.rawSignal,
    Correct: s.correct === null ? "N/A" : s.correct ? "Yes" : "No",
    Score: s.score ?? "",
    Band: s.scoreBand ?? "",
    Confidence: s.confidence ?? "",
    "Conflict?": s.conflictDetected != null ? (s.conflictDetected ? "Yes" : "No") : "",
    "Tech Score": s.techScore ?? "",
    "Fund Score": s.fundScore ?? "",
  };
}

/* ── Summary row per agent ───────────────────────────────── */

function summaryRow(a: AgentSummary) {
  return {
    Agent: a.agent,
    "Total Periods": a.totalPeriods,
    "Total Trades": a.totalTrades,
    Correct: a.correct,
    Incorrect: a.incorrect,
    "Win Rate %": a.winRate ?? "",
    Buys: a.buys,
    Sells: a.sells,
    Holds: a.holds,
    Tickers: a.tickers.join(", "),
  };
}

/* ── Confusion matrix row ────────────────────────────────── */

function cmRow(label: string, cm: ConfusionMatrix) {
  const trades = cm.buyUp + cm.buyDown + cm.sellUp + cm.sellDown;
  const correct = cm.buyUp + cm.sellDown;
  return {
    Label: label,
    "Buy→Up (TP)": cm.buyUp,
    "Buy→Down (FP)": cm.buyDown,
    "Sell→Up (FN)": cm.sellUp,
    "Sell→Down (TN)": cm.sellDown,
    "Hold→Up": cm.holdUp,
    "Hold→Down": cm.holdDown,
    "Win Rate %": trades > 0 ? Math.round((correct / trades) * 1000) / 10 : "",
  };
}

/* ── Main export function ────────────────────────────────── */

export function exportToExcel(data: DashboardData): void {
  const wb = XLSX.utils.book_new();

  // 1. Signals sheet
  const signalRows = data.signals.map(signalRow);
  const ws1 = XLSX.utils.json_to_sheet(signalRows);
  XLSX.utils.book_append_sheet(wb, ws1, "Signals");

  // 2. Summary sheet
  const summaryRows = data.summaries.map(summaryRow);
  const ws2 = XLSX.utils.json_to_sheet(summaryRows);
  XLSX.utils.book_append_sheet(wb, ws2, "Agent Summary");

  // 3. Confusion Matrix sheet
  const cmRows: ReturnType<typeof cmRow>[] = [];
  for (const s of data.summaries) {
    cmRows.push(cmRow(`${s.agent} (Overall)`, s.cm));
    for (const [sec, sData] of Object.entries(s.bySector)) {
      cmRows.push(cmRow(`${s.agent} — ${sec}`, sData.cm));
    }
  }
  const ws3 = XLSX.utils.json_to_sheet(cmRows);
  XLSX.utils.book_append_sheet(wb, ws3, "Confusion Matrices");

  // 4. Sector Breakdown sheet
  const sectorRows: Record<string, unknown>[] = [];
  for (const s of data.summaries) {
    for (const [sec, sData] of Object.entries(s.bySector)) {
      sectorRows.push({
        Agent: s.agent,
        Sector: sec,
        Periods: sData.totalPeriods,
        Trades: sData.totalTrades,
        Correct: sData.correct,
        "Win Rate %": sData.winRate ?? "",
        Buys: sData.buys,
        Sells: sData.sells,
        Holds: sData.holds,
      });
    }
  }
  const ws4 = XLSX.utils.json_to_sheet(sectorRows);
  XLSX.utils.book_append_sheet(wb, ws4, "Sector Breakdown");

  // Generate and download
  const filename = `backtest_results_${data.meta.generated}.xlsx`;
  XLSX.writeFile(wb, filename);
}
