import type { Signal, ConfusionMatrix } from "./types";

export function winRate(signals: Signal[]): number {
  const trades = signals.filter((s) => s.correct !== null);
  if (trades.length === 0) return 0;
  return (trades.filter((s) => s.correct).length / trades.length) * 100;
}

export function sharpeRatio(signals: Signal[]): number {
  const returns = signals
    .filter((s) => s.signal !== "HOLD")
    .map((s) => (s.signal === "SELL" ? -s.returnPct : s.returnPct));
  if (returns.length < 2) return 0;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const std = Math.sqrt(
    returns.reduce((sum, r) => sum + (r - mean) ** 2, 0) / (returns.length - 1)
  );
  if (std === 0) return 0;
  return (mean / std) * Math.sqrt(12);
}

export function maxDrawdown(signals: Signal[]): number {
  const returns = signals
    .filter((s) => s.signal !== "HOLD")
    .map((s) => (s.signal === "SELL" ? -s.returnPct : s.returnPct));
  let peak = 0;
  let cumulative = 0;
  let maxDd = 0;
  for (const r of returns) {
    cumulative += r;
    if (cumulative > peak) peak = cumulative;
    const dd = peak - cumulative;
    if (dd > maxDd) maxDd = dd;
  }
  return maxDd;
}

export function profitFactor(signals: Signal[]): number {
  let gains = 0;
  let losses = 0;
  for (const s of signals) {
    if (s.signal === "HOLD") continue;
    const ret = s.signal === "SELL" ? -s.returnPct : s.returnPct;
    if (ret > 0) gains += ret;
    else losses += Math.abs(ret);
  }
  return losses === 0 ? (gains > 0 ? Infinity : 0) : gains / losses;
}

export function buildConfusionMatrix(signals: Signal[]): ConfusionMatrix {
  const cm: ConfusionMatrix = { buyUp: 0, buyDown: 0, sellUp: 0, sellDown: 0, holdUp: 0, holdDown: 0 };
  for (const s of signals) {
    const key = `${s.signal.toLowerCase()}${s.actualDirection === "up" ? "Up" : "Down"}` as keyof ConfusionMatrix;
    if (key in cm) cm[key]++;
  }
  return cm;
}

export function avgReturn(signals: Signal[]): number {
  const trades = signals.filter((s) => s.signal !== "HOLD");
  if (trades.length === 0) return 0;
  return trades.reduce((sum, s) => sum + s.returnPct, 0) / trades.length;
}
