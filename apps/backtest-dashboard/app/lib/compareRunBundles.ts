/**
 * Mirrors scripts/lib/run_bundle.py compare_bundles() for the dashboard.
 * Keep behavior aligned when changing delta semantics.
 */

export type RunBundle = {
  schema_version?: string;
  run_id?: string;
  as_of_date?: string;
  fusion?: string;
  rows?: BundleRow[];
};

export type BundleRow = {
  ticker: string;
  sector?: string | null;
  fusion_final_signal?: string | null;
  fusion_orchestrator_score?: number | null;
  phoenix_signal?: string | null;
  error?: string | null;
};

export type ComparisonDoc = {
  schema_version: string;
  summary: {
    tickers_compared: number;
    signal_changes: number;
    added: number;
    removed: number;
  };
  per_ticker: Record<
    string,
    {
      status: string;
      changed?: boolean;
      fusion_signal?: { from: string | null | undefined; to: string | null | undefined };
      phoenix_signal?: { from: string | null | undefined; to: string | null | undefined };
      fusion_score_delta?: number | null;
      row_a?: BundleRow;
      row_b?: BundleRow;
    }
  >;
};

export function compareRunBundles(a: RunBundle, b: RunBundle): ComparisonDoc {
  const rowsA = Object.fromEntries((a.rows ?? []).map((r) => [r.ticker.toUpperCase(), r]));
  const rowsB = Object.fromEntries((b.rows ?? []).map((r) => [r.ticker.toUpperCase(), r]));
  const tickers = Array.from(new Set([...Object.keys(rowsA), ...Object.keys(rowsB)])).sort();

  const per_ticker: ComparisonDoc["per_ticker"] = {};
  let signalChanges = 0;
  let added = 0;
  let removed = 0;

  for (const t of tickers) {
    const ra = rowsA[t];
    const rb = rowsB[t];
    if (!ra) {
      per_ticker[t] = { status: "added_in_b", row_b: rb };
      added++;
      continue;
    }
    if (!rb) {
      per_ticker[t] = { status: "removed_in_b", row_a: ra };
      removed++;
      continue;
    }
    let fusion_score_delta: number | null = null;
    const sa = ra.fusion_orchestrator_score;
    const sb = rb.fusion_orchestrator_score;
    if (typeof sa === "number" && typeof sb === "number") {
      fusion_score_delta = Math.round((sb - sa) * 1e4) / 1e4;
    }
    const changed =
      ra.fusion_final_signal !== rb.fusion_final_signal ||
      ra.phoenix_signal !== rb.phoenix_signal ||
      (fusion_score_delta !== null && Math.abs(fusion_score_delta) > 1e-6);
    if (changed) signalChanges++;
    per_ticker[t] = {
      status: "both",
      changed,
      fusion_signal: { from: ra.fusion_final_signal, to: rb.fusion_final_signal },
      phoenix_signal: { from: ra.phoenix_signal, to: rb.phoenix_signal },
      fusion_score_delta,
      row_a: ra,
      row_b: rb,
    };
  }

  return {
    schema_version: "1.0.0",
    summary: {
      tickers_compared: tickers.length,
      signal_changes: signalChanges,
      added,
      removed,
    },
    per_ticker,
  };
}
