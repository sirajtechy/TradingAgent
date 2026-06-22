"use client";

import { Suspense } from "react";
import TechnicalBacktestLab from "./TechnicalBacktestLab";

export default function BacktestsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 text-sm text-[var(--text-dim)]">Loading technical backtest…</div>
      }
    >
      <TechnicalBacktestLab />
    </Suspense>
  );
}
