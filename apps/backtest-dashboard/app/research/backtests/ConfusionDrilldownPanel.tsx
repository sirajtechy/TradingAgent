"use client";

import Link from "next/link";
import {
  BUCKET_COLORS,
  BUCKET_LABELS,
  type ConfusionBucket,
  type TickerDrilldownRow,
  agentDrilldownSpec,
} from "@/app/lib/confusionBucket";
import { AGENT_LABELS } from "./AgentMatrixHeatmap";
import { TradeDrilldownTable, tradeDrilldownFootnote } from "./TradeDrilldownTable";

export function ConfusionDrilldownPanel({
  agentId,
  bucket,
  tickers,
  onClose,
  showTradeColumns = true,
}: {
  agentId: string;
  bucket: ConfusionBucket;
  tickers: TickerDrilldownRow[];
  onClose?: () => void;
  showTradeColumns?: boolean;
}) {
  const spec = agentDrilldownSpec(agentId);
  const agentLabel = spec?.label || AGENT_LABELS[agentId] || agentId;

  return (
    <section className={`rounded-lg border p-4 text-sm ${BUCKET_COLORS[bucket]}`}>
      <div className="flex flex-wrap items-start gap-3 mb-3">
        <div>
          <h2 className="font-semibold">
            {BUCKET_LABELS[bucket]} · {agentLabel}
          </h2>
          <p className="text-xs opacity-80 mt-0.5">
            {tickers.length} ticker{tickers.length === 1 ? "" : "s"} in this cell
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="ml-auto text-xs border border-current/30 rounded px-2 py-1 hover:bg-white/5"
          >
            Close
          </button>
        )}
      </div>
      {tickers.length === 0 ? (
        <p className="text-xs opacity-80">No tickers in this bucket for the selected run.</p>
      ) : (
        <TradeDrilldownTable rows={tickers} showTradeColumns={showTradeColumns} />
      )}
      <p className="text-[10px] opacity-70 mt-2">
        {tradeDrilldownFootnote(showTradeColumns)}{" "}
        <Link href="/research/analyze" className="underline">
          Deep analyze
        </Link>{" "}
        any symbol from Research Lab.
      </p>
    </section>
  );
}
