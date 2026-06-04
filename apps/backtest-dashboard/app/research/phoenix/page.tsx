"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowDown,
  ArrowUp,
  Crosshair,
  Eye,
  FileSpreadsheet,
  ShoppingCart,
} from "lucide-react";
import * as XLSX from "xlsx";
import { confusionBucket, confusionCells, type ConfusionBucket } from "../../lib/confusionBucket";
import {
  extensionJustificationText,
  isTradeFocusRow,
  shouldShowExtensionJustification,
  WATCH_EXTENSION_MIN_SCORE,
} from "../../lib/extensionDisplay";

type SortKey =
  | "ticker"
  | "phoenix"
  | "fusion"
  | "tp"
  | "fp"
  | "tn"
  | "fn"
  | "category"
  | "entry"
  | "exit"
  | "stop"
  | "target1"
  | "target2"
  | "hypT1"
  | "hypT2"
  | "ext5d"
  | "ext4w"
  | "chaseRisk"
  | "alreadyUp"
  | "phoenixScore"
  | "pattern";

const PHOENIX_ORDER: Record<string, number> = { BUY: 0, WATCH: 1, AVOID: 2 };
const FUSION_ORDER: Record<string, number> = { bullish: 0, bearish: 1, neutral: 2 };
const BUCKET_ORDER: Record<ConfusionBucket, number> = {
  TP: 0,
  FP: 1,
  TN: 2,
  FN: 3,
  NEUTRAL: 4,
  UNLABELED: 5,
};
const CHASE_ORDER: Record<string, number> = { low: 0, moderate: 1, elevated: 2, unknown: 3 };

function numOrNull(v: number | null | undefined): number | null {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return null;
  return Number(v);
}

function compareNullableNum(a: number | null, b: number | null, dir: "asc" | "desc"): number {
  const aBad = a === null;
  const bBad = b === null;
  if (aBad && bBad) return 0;
  if (aBad) return dir === "asc" ? 1 : -1;
  if (bBad) return dir === "asc" ? -1 : 1;
  const cmp = a - b;
  return dir === "asc" ? cmp : -cmp;
}

function SortableTh({
  col,
  label,
  sortColumn,
  sortDir,
  onSort,
  className = "",
  title,
  align = "left",
}: {
  col: SortKey;
  label: string;
  sortColumn: SortKey;
  sortDir: "asc" | "desc";
  onSort: (c: SortKey) => void;
  className?: string;
  title?: string;
  align?: "left" | "center" | "right";
}) {
  const active = sortColumn === col;
  const justify = align === "center" ? "justify-center" : align === "right" ? "justify-end" : "justify-start";
  const textAlign = align === "center" ? "text-center" : align === "right" ? "text-right" : "text-left";
  return (
    <th className={`px-3 py-3 font-medium ${textAlign} ${className}`} title={title}>
      <button
        type="button"
        onClick={() => onSort(col)}
        className={`inline-flex items-center gap-1.5 w-full ${justify} uppercase tracking-wide hover:text-indigo-300 transition-colors ${
          active ? "text-indigo-300" : ""
        }`}
      >
        <span>{label}</span>
        {active ? (
          sortDir === "asc" ? (
            <ArrowUp size={14} className="shrink-0 opacity-90" />
          ) : (
            <ArrowDown size={14} className="shrink-0 opacity-90" />
          )
        ) : (
          <span className="text-[var(--text-dim)] opacity-40 shrink-0 text-[10px] font-normal normal-case">↕</span>
        )}
      </button>
    </th>
  );
}

type RunItem = { id: string; relPath: string; modified: string; kind?: string };

/** Default master run: ?rel= query → otherwise newest master_pilot.json by modified time. */
function pickDefaultMasterId(masters: RunItem[], relFromQuery: string | null): string {
  if (relFromQuery) {
    const decoded = decodeURIComponent(relFromQuery.trim());
    const hit = masters.find((x) => x.relPath === decoded || x.relPath === relFromQuery.trim());
    if (hit) return hit.id;
  }
  if (masters.length === 0) return "";
  // API returns masters newest-first; prefer top-level unified_master_* over nested sector shards.
  const unifiedRoot = masters.find(
    (x) => /\/unified_master_[^/]+\/master_pilot\.json$/i.test(x.relPath),
  );
  return (unifiedRoot ?? masters[0]).id;
}

type MasterDoc = {
  schema_version?: string;
  run_id?: string;
  manifest?: { signal_date?: string; result_date?: string; universe_label?: string };
  tickers?: Record<string, MasterTickerRow>;
};

/** Plain row for spreadsheet export */
function rowToExcelRecord(
  r: MasterTickerRow & { ticker: string },
): Record<string, string | number | boolean | null> {
  const b = confusionBucket(r.fusion_final_signal, r.signal_correct);
  const cells = confusionCells(b);
  return {
    Ticker: r.ticker,
    Phoenix: ((r.phoenix_signal || "") as string).toUpperCase(),
    Fusion: r.fusion_final_signal ?? "",
    Category: b,
    TP: cells.TP ? 1 : 0,
    FP: cells.FP ? 1 : 0,
    TN: cells.TN ? 1 : 0,
    FN: cells.FN ? 1 : 0,
    Entry: r.entry_price ?? "",
    Exit_ref: r.exit_price ?? "",
    Stop: r.stop_price ?? "",
    Target_1: r.target_t1 ?? "",
    Target_2: r.target_t2 ?? "",
    Backtest_target: r.backtest_target_price ?? "",
    Hypothetical_pct_T1: r.hypothetical_long_profit_pct_to_t1 ?? "",
    Hypothetical_pct_T2: r.hypothetical_long_profit_pct_to_t2 ?? "",
    Extension_justification: shouldShowExtensionJustification(r)
      ? extensionJustificationText(r) ?? ""
      : "",
    Extension_summary: r.extension_summary ?? "",
    Extension_5d_pct: r.extension_daily_5d_pct ?? "",
    Extension_4w_pct: r.extension_weekly_4w_pct ?? "",
    Chase_risk: r.chase_risk ?? "",
    Fusion_score: r.fusion_orchestrator_score ?? "",
    Phoenix_score: r.phoenix_score ?? "",
    Fund_score: r.fund_score ?? "",
    Pattern: r.pattern_name ?? "",
    Target_hit: r.target_hit ?? "",
  };
}

function safeFilename(part: string): string {
  return part.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 80);
}

type MasterTickerRow = {
  error?: string;
  phoenix_signal?: string | null;
  fusion_final_signal?: string | null;
  signal_correct?: boolean | null;
  fusion_orchestrator_score?: number | null;
  phoenix_score?: number | null;
  fund_score?: number | null;
  entry_price?: number | null;
  exit_price?: number | null;
  stop_price?: number | null;
  target_t1?: number | null;
  target_t2?: number | null;
  backtest_target_price?: number | null;
  hypothetical_long_profit_pct_to_t1?: number | null;
  hypothetical_long_profit_pct_to_t2?: number | null;
  extension_daily_5d_pct?: number | null;
  extension_weekly_4w_pct?: number | null;
  extension_justification?: string | null;
  extension_summary?: string | null;
  extension_guardrail?: Record<string, unknown> | null;
  chase_risk?: string | null;
  target_hit?: boolean | null;
  pattern_name?: string | null;
};

const CONFUSION_MARK_KEY: Record<"tp" | "fp" | "tn" | "fn", keyof ReturnType<typeof confusionCells>> = {
  tp: "TP",
  fp: "FP",
  tn: "TN",
  fn: "FN",
};

function sortRows(
  list: (MasterTickerRow & { ticker: string })[],
  key: SortKey,
  dir: "asc" | "desc",
): (MasterTickerRow & { ticker: string })[] {
  const mul = dir === "asc" ? 1 : -1;
  const out = [...list];
  out.sort((ra, rb) => {
    switch (key) {
      case "ticker":
        return mul * ra.ticker.localeCompare(rb.ticker);
      case "phoenix": {
        const pa = PHOENIX_ORDER[(ra.phoenix_signal || "").toUpperCase()] ?? 99;
        const pb = PHOENIX_ORDER[(rb.phoenix_signal || "").toUpperCase()] ?? 99;
        return mul * (pa - pb) || ra.ticker.localeCompare(rb.ticker);
      }
      case "fusion": {
        const fa = FUSION_ORDER[(ra.fusion_final_signal || "").toLowerCase()] ?? 99;
        const fb = FUSION_ORDER[(rb.fusion_final_signal || "").toLowerCase()] ?? 99;
        return mul * (fa - fb) || ra.ticker.localeCompare(rb.ticker);
      }
      case "tp":
      case "fp":
      case "tn":
      case "fn": {
        const ba = confusionBucket(ra.fusion_final_signal, ra.signal_correct);
        const bb = confusionBucket(rb.fusion_final_signal, rb.signal_correct);
        const ma = confusionCells(ba);
        const mb = confusionCells(bb);
        const mk = CONFUSION_MARK_KEY[key];
        const va = ma[mk] ? 1 : 0;
        const vb = mb[mk] ? 1 : 0;
        return mul * (va - vb) || ra.ticker.localeCompare(rb.ticker);
      }
      case "category": {
        const ba = confusionBucket(ra.fusion_final_signal, ra.signal_correct);
        const bb = confusionBucket(rb.fusion_final_signal, rb.signal_correct);
        const oa = BUCKET_ORDER[ba];
        const ob = BUCKET_ORDER[bb];
        return mul * (oa - ob) || ra.ticker.localeCompare(rb.ticker);
      }
      case "entry":
        return compareNullableNum(numOrNull(ra.entry_price), numOrNull(rb.entry_price), dir) || ra.ticker.localeCompare(rb.ticker);
      case "exit":
        return compareNullableNum(numOrNull(ra.exit_price), numOrNull(rb.exit_price), dir) || ra.ticker.localeCompare(rb.ticker);
      case "stop":
        return compareNullableNum(numOrNull(ra.stop_price), numOrNull(rb.stop_price), dir) || ra.ticker.localeCompare(rb.ticker);
      case "target1":
        return compareNullableNum(numOrNull(ra.target_t1), numOrNull(rb.target_t1), dir) || ra.ticker.localeCompare(rb.ticker);
      case "target2":
        return compareNullableNum(numOrNull(ra.target_t2), numOrNull(rb.target_t2), dir) || ra.ticker.localeCompare(rb.ticker);
      case "hypT1":
        return (
          compareNullableNum(numOrNull(ra.hypothetical_long_profit_pct_to_t1), numOrNull(rb.hypothetical_long_profit_pct_to_t1), dir) ||
          ra.ticker.localeCompare(rb.ticker)
        );
      case "hypT2":
        return (
          compareNullableNum(numOrNull(ra.hypothetical_long_profit_pct_to_t2), numOrNull(rb.hypothetical_long_profit_pct_to_t2), dir) ||
          ra.ticker.localeCompare(rb.ticker)
        );
      case "ext5d":
        return (
          compareNullableNum(numOrNull(ra.extension_daily_5d_pct), numOrNull(rb.extension_daily_5d_pct), dir) ||
          ra.ticker.localeCompare(rb.ticker)
        );
      case "ext4w":
        return (
          compareNullableNum(numOrNull(ra.extension_weekly_4w_pct), numOrNull(rb.extension_weekly_4w_pct), dir) ||
          ra.ticker.localeCompare(rb.ticker)
        );
      case "chaseRisk": {
        const ca = CHASE_ORDER[(ra.chase_risk || "unknown").toLowerCase()] ?? 99;
        const cb = CHASE_ORDER[(rb.chase_risk || "unknown").toLowerCase()] ?? 99;
        return mul * (ca - cb) || ra.ticker.localeCompare(rb.ticker);
      }
      case "alreadyUp":
        return (
          compareNullableNum(numOrNull(ra.extension_daily_5d_pct), numOrNull(rb.extension_daily_5d_pct), dir) ||
          ra.ticker.localeCompare(rb.ticker)
        );
      case "phoenixScore":
        return (
          compareNullableNum(numOrNull(ra.phoenix_score), numOrNull(rb.phoenix_score), dir) || ra.ticker.localeCompare(rb.ticker)
        );
      case "pattern": {
        const pa = (ra.pattern_name || "").toLowerCase();
        const pb = (rb.pattern_name || "").toLowerCase();
        return mul * pa.localeCompare(pb) || ra.ticker.localeCompare(rb.ticker);
      }
      default:
        return 0;
    }
  });
  return out;
}

function fmtNum(v: number | null | undefined, d = 2): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(d);
}

function pctParts(v: number | null | undefined): { text: string; tone: "pos" | "neg" | "empty" } {
  if (v === null || v === undefined || Number.isNaN(Number(v))) {
    return { text: "—", tone: "empty" };
  }
  const n = Number(v);
  return {
    text: `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`,
    tone: n >= 0 ? "pos" : "neg",
  };
}

function PctCell({ v }: { v: number | null | undefined }) {
  const { text, tone } = pctParts(v);
  const cls =
    tone === "empty" ? "text-[var(--text-dim)]" : tone === "pos" ? "text-emerald-400" : "text-red-400";
  return <span className={cls}>{text}</span>;
}

export default function PhoenixWatchBuyPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selected, setSelected] = useState("");
  const [doc, setDoc] = useState<MasterDoc | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  /** BUY+WATCH only vs full run (every ticker) for confusion columns */
  const [viewAllTickers, setViewAllTickers] = useState(false);
  /** BUY + WATCH with Phoenix score > 60 (trade focus list) */
  const [tradeFocus, setTradeFocus] = useState(false);
  const [sortColumn, setSortColumn] = useState<SortKey>("ticker");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const masterRuns = useMemo(() => runs.filter((r) => r.kind === "master"), [runs]);

  useEffect(() => {
    fetch("/api/trading-runs")
      .then((r) => r.json())
      .then((d) => {
        const list: RunItem[] = d.runs ?? [];
        setRuns(list);
        const masters = list.filter((x: RunItem) => x.kind === "master");
        if (!masters.length) return;
        setSelected((prev) => {
          if (prev) return prev;
          let relQ: string | null = null;
          if (typeof window !== "undefined") {
            relQ = new URLSearchParams(window.location.search).get("rel");
          }
          return pickDefaultMasterId(masters, relQ);
        });
      })
      .catch(() => setErr("Failed to list runs"));
  }, []);

  useEffect(() => {
    if (!selected) {
      setDoc(null);
      return;
    }
    const rel = runs.find((x) => x.id === selected)?.relPath;
    if (!rel) return;
    setLoading(true);
    setErr(null);
    fetch(`/api/trading-runs/bundle?rel=${encodeURIComponent(rel)}`)
      .then((r) => r.json())
      .then((d: MasterDoc) => {
        if ((d as { error?: string }).error) throw new Error((d as { error: string }).error);
        if (!d.tickers || typeof d.tickers !== "object") {
          throw new Error("Not a master_pilot.json (missing tickers map). Pick a master run.");
        }
        setDoc(d);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [selected, runs]);

  useEffect(() => {
    setSortColumn("ticker");
    setSortDir("asc");
  }, [selected, doc?.run_id]);

  const onSortHeader = useCallback((col: SortKey) => {
    setSortColumn((prev) => {
      if (prev === col) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return prev;
      }
      setSortDir("asc");
      return col;
    });
  }, []);

  const allRows = useMemo(() => {
    if (!doc?.tickers) return [];
    const out: (MasterTickerRow & { ticker: string })[] = [];
    for (const [ticker, row] of Object.entries(doc.tickers)) {
      if (!row || typeof row !== "object") continue;
      if (row.error) continue;
      out.push({ ...row, ticker });
    }
    out.sort((a, b) => a.ticker.localeCompare(b.ticker));
    return out;
  }, [doc]);

  const rows = useMemo(() => {
    let list = viewAllTickers
      ? allRows
      : allRows.filter((r) => {
          const px = (r.phoenix_signal || "").toUpperCase();
          return px === "BUY" || px === "WATCH";
        });
    if (tradeFocus) {
      list = list.filter((r) => isTradeFocusRow(r));
    }
    return list;
  }, [allRows, viewAllTickers, tradeFocus]);

  const buyN = allRows.filter((r) => (r.phoenix_signal || "").toUpperCase() === "BUY").length;
  const watchN = allRows.filter((r) => (r.phoenix_signal || "").toUpperCase() === "WATCH").length;
  const bucketCounts = useMemo(() => {
    const c: Record<ConfusionBucket, number> = { TP: 0, FP: 0, TN: 0, FN: 0, NEUTRAL: 0, UNLABELED: 0 };
    for (const r of rows) c[confusionBucket(r.fusion_final_signal, r.signal_correct)] += 1;
    return c;
  }, [rows]);

  const sortedRows = useMemo(() => sortRows(rows, sortColumn, sortDir), [rows, sortColumn, sortDir]);

  const hasExtensionData = useMemo(() => {
    return allRows.some(
      (r) =>
        Boolean(r.extension_justification?.trim()) ||
        r.extension_daily_5d_pct != null ||
        Boolean(r.extension_guardrail),
    );
  }, [allRows]);

  const downloadExcel = useCallback(() => {
    if (!doc || sortedRows.length === 0) return;
    const rel = runs.find((x) => x.id === selected)?.relPath ?? "run";
    const wb = XLSX.utils.book_new();
    const data = sortedRows.map(rowToExcelRecord);
    const ws = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, viewAllTickers ? "All_tickers" : "BUY_WATCH");
    const metaRows = [
      { Key: "run_id", Value: doc.run_id ?? "" },
      { Key: "signal_date", Value: doc.manifest?.signal_date ?? "" },
      { Key: "result_date", Value: doc.manifest?.result_date ?? "" },
      { Key: "universe", Value: doc.manifest?.universe_label ?? "" },
      { Key: "source_file", Value: rel },
      { Key: "rows_exported", Value: sortedRows.length },
      { Key: "view_all_tickers", Value: viewAllTickers ? "yes" : "no" },
    ];
    const wsMeta = XLSX.utils.json_to_sheet(metaRows);
    XLSX.utils.book_append_sheet(wb, wsMeta, "Meta");
    const sig = doc.manifest?.signal_date ?? "nodate";
    const leaf = rel.split("/").pop()?.replace(/\.json$/i, "") ?? "phoenix_buy_watch";
    const base = safeFilename(leaf);
    XLSX.writeFile(wb, `${base}_${sig}.xlsx`);
  }, [doc, sortedRows, runs, selected, viewAllTickers]);

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)] px-6 py-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
              <Crosshair className="text-indigo-400" size={22} />
              Phoenix BUY &amp; WATCH
            </h1>
            <p className="text-sm text-[var(--text-dim)] mt-1 max-w-3xl">
              Toggle <strong className="text-[var(--text)]">All tickers</strong> for TP/FP/TN/FN on every symbol.{" "}
              Column <strong className="text-[var(--text)]">Already up</strong> shows how far price moved before the signal (no future data): all{" "}
              <span className="text-emerald-400">BUY</span>, and{" "}
              <span className="text-amber-400">WATCH</span> with Phoenix score &gt; {WATCH_EXTENSION_MIN_SCORE}. Re-run sectors after guardrail update to populate.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-[var(--text-dim)] cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={tradeFocus}
                onChange={(e) => setTradeFocus(e.target.checked)}
                className="rounded border-[var(--border)]"
              />
              <span>Trade focus (BUY + WATCH score&gt;{WATCH_EXTENSION_MIN_SCORE})</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-[var(--text-dim)] cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={viewAllTickers}
                onChange={(e) => setViewAllTickers(e.target.checked)}
                className="rounded border-[var(--border)]"
              />
              <span>All tickers ({allRows.length})</span>
            </label>
            <label className="text-xs text-[var(--text-dim)] uppercase tracking-wider">Run</label>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="bg-[#1a1a24] border border-[var(--border)] rounded-lg px-3 py-2 text-sm min-w-[240px] max-w-[min(100vw-3rem,420px)]"
            >
              {masterRuns.length === 0 && <option value="">No master_pilot.json found</option>}
              {masterRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.relPath.replace(/^data\/output\/trading_runs\//, "")} · {r.modified.slice(0, 10)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {doc?.manifest?.signal_date && (
          <p className="text-xs text-[var(--text-dim)] mt-3">
            Signal <span className="text-[var(--text)]">{doc.manifest.signal_date}</span>
            {doc.manifest.result_date ? (
              <>
                {" "}
                → result window end <span className="text-[var(--text)]">{doc.manifest.result_date}</span>
              </>
            ) : null}
            {doc.manifest.universe_label ? ` · ${doc.manifest.universe_label}` : ""}
          </p>
        )}
      </header>

      <div className="p-6 max-w-[1800px] mx-auto">
        {err && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {err}
          </div>
        )}

        {loading && <p className="text-sm text-[var(--text-dim)]">Loading…</p>}

        {!loading && doc && !hasExtensionData && (
          <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            This run has no extension / &quot;Already up&quot; data (likely an older backtest). Pick your newest{" "}
            <strong>unified_master_*</strong> run from the dropdown above, or re-run:{" "}
            <code className="text-amber-100">./bin/mts lab unified</code>
          </div>
        )}

        {!loading && doc && (
          <>
            <div className="flex flex-wrap gap-3 mb-6">
              <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-4 py-1.5 text-sm">
                <ShoppingCart size={16} className="text-emerald-400" />
                <span className="text-[var(--text-dim)]">BUY</span>
                <span className="font-semibold text-emerald-400">{buyN}</span>
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-amber-500/15 border border-amber-500/30 px-4 py-1.5 text-sm">
                <Eye size={16} className="text-amber-400" />
                <span className="text-[var(--text-dim)]">WATCH</span>
                <span className="font-semibold text-amber-400">{watchN}</span>
              </span>
              <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 rounded-full bg-white/5 border border-[var(--border)] px-4 py-1.5 text-sm text-[var(--text-dim)]">
                <span className="text-[var(--text)] font-medium">Confusion (this view)</span>
                <span className="text-emerald-300 font-semibold">TP {bucketCounts.TP}</span>
                <span className="text-red-300 font-semibold">FP {bucketCounts.FP}</span>
                <span className="text-cyan-300 font-semibold">TN {bucketCounts.TN}</span>
                <span className="text-amber-300 font-semibold">FN {bucketCounts.FN}</span>
                <span className="text-[var(--text-dim)]">Neutral {bucketCounts.NEUTRAL}</span>
                <span className="text-[var(--text-dim)]">Unlabeled {bucketCounts.UNLABELED}</span>
              </span>
              <span className="inline-flex items-center rounded-full bg-white/5 border border-[var(--border)] px-4 py-1.5 text-sm text-[var(--text-dim)]">
                Showing <strong className="text-[var(--text)] mx-1">{rows.length}</strong> rows
              </span>
              <button
                type="button"
                onClick={downloadExcel}
                disabled={sortedRows.length === 0}
                className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 disabled:pointer-events-none transition-colors"
              >
                <FileSpreadsheet size={18} />
                Download Excel (.xlsx)
              </button>
            </div>

            <p className="text-xs text-[var(--text-dim)] mb-2">
              Sort: <span className="text-[var(--text)] font-mono">{sortColumn}</span> ({sortDir}) — click any column header to sort; click again to reverse.
            </p>
            <div className="rounded-xl border border-[var(--border)] overflow-hidden bg-[var(--bg-card)] shadow-xl shadow-black/20">
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-[#15151f] text-left text-[var(--text-dim)] text-xs uppercase tracking-wide border-b border-[var(--border)]">
                      <SortableTh
                        col="ticker"
                        label="Ticker"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        className="sticky left-0 bg-[#15151f] z-10 min-w-[88px]"
                      />
                      <SortableTh col="phoenix" label="Phoenix" sortColumn={sortColumn} sortDir={sortDir} onSort={onSortHeader} />
                      <SortableTh
                        col="phoenixScore"
                        label="Px score"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="alreadyUp"
                        label="Already up"
                        title="How much price moved before signal (BUY all; WATCH if score > 60)"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        className="min-w-[200px]"
                      />
                      <SortableTh col="fusion" label="Fusion" sortColumn={sortColumn} sortDir={sortDir} onSort={onSortHeader} />
                      <SortableTh
                        col="tp"
                        label="TP"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="center"
                        className="w-14"
                        title="True positive: bullish + correct"
                      />
                      <SortableTh
                        col="fp"
                        label="FP"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="center"
                        className="w-14"
                        title="False positive: bullish + incorrect"
                      />
                      <SortableTh
                        col="tn"
                        label="TN"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="center"
                        className="w-14"
                        title="True negative: bearish + correct"
                      />
                      <SortableTh
                        col="fn"
                        label="FN"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="center"
                        className="w-14"
                        title="False negative: bearish + incorrect"
                      />
                      <SortableTh col="category" label="Category" sortColumn={sortColumn} sortDir={sortDir} onSort={onSortHeader} />
                      <SortableTh
                        col="entry"
                        label="Entry"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="exit"
                        label="Exit (ref)"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh col="stop" label="Stop" sortColumn={sortColumn} sortDir={sortDir} onSort={onSortHeader} align="right" />
                      <SortableTh
                        col="target1"
                        label="Target 1"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="target2"
                        label="Target 2"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="hypT1"
                        label="Upside T1"
                        title="Required % move from entry to Target 1 (not realized rally)"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="hypT2"
                        label="Upside T2"
                        title="Required % move from entry to Target 2"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="ext5d"
                        label="5d %"
                        title="Price change over last 5 daily bars at signal date"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="ext4w"
                        label="4w %"
                        title="Price change over last 4 weekly bars at signal date"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                        align="right"
                      />
                      <SortableTh
                        col="chaseRisk"
                        label="Chase"
                        title="Extension / chase risk at signal (BUY unchanged)"
                        sortColumn={sortColumn}
                        sortDir={sortDir}
                        onSort={onSortHeader}
                      />
                      <SortableTh col="pattern" label="Pattern" sortColumn={sortColumn} sortDir={sortDir} onSort={onSortHeader} />
                    </tr>
                  </thead>
                  <tbody>
                    {sortedRows.map((r) => {
                      const px = (r.phoenix_signal || "").toUpperCase();
                      const bucket = confusionBucket(r.fusion_final_signal, r.signal_correct);
                      const marks = confusionCells(bucket);
                      const badge =
                        px === "BUY" ? (
                          <span className="rounded-md bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-xs font-semibold">
                            BUY
                          </span>
                        ) : px === "WATCH" ? (
                          <span className="rounded-md bg-amber-500/20 text-amber-400 px-2 py-0.5 text-xs font-semibold">
                            WATCH
                          </span>
                        ) : (
                          <span className="rounded-md bg-white/10 text-[var(--text-dim)] px-2 py-0.5 text-xs font-semibold">
                            {px || "—"}
                          </span>
                        );
                      const markBase = "text-center font-mono text-base font-bold";
                      const emptyCls = "text-center text-[var(--text-dim)]";
                      const showExt = shouldShowExtensionJustification(r);
                      const extText = showExt ? extensionJustificationText(r) : null;
                      const extTitle = showExt
                        ? [r.extension_summary, r.chase_risk ? `Chase: ${r.chase_risk}` : null]
                            .filter(Boolean)
                            .join(" · ")
                        : px === "WATCH"
                          ? `WATCH with score ≤ ${WATCH_EXTENSION_MIN_SCORE} — extension hidden`
                          : undefined;
                      return (
                        <tr
                          key={r.ticker}
                          className="border-b border-[var(--border)]/80 hover:bg-white/[0.03] transition-colors"
                        >
                          <td className="px-3 py-2.5 font-mono font-semibold text-cyan-300/90 sticky left-0 bg-[var(--bg-card)] z-10">
                            {r.ticker}
                          </td>
                          <td className="px-3 py-2.5">{badge}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums text-[var(--text-dim)]">
                            {fmtNum(r.phoenix_score, 1)}
                          </td>
                          <td
                            className="px-3 py-2.5 text-xs text-[var(--text-dim)] max-w-[280px]"
                            title={extTitle || extText || ""}
                          >
                            {showExt && extText ? (
                              <span className="text-[var(--text)] leading-snug">{extText}</span>
                            ) : showExt ? (
                              <span className="text-[var(--text-dim)] italic">Re-run for extension data</span>
                            ) : (
                              <span className="text-[var(--text-dim)]">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-[var(--text-dim)] capitalize">
                            {r.fusion_final_signal ?? "—"}
                          </td>
                          <td className={marks.TP ? `${markBase} text-emerald-400` : emptyCls}>{marks.TP || "—"}</td>
                          <td className={marks.FP ? `${markBase} text-red-400` : emptyCls}>{marks.FP || "—"}</td>
                          <td className={marks.TN ? `${markBase} text-cyan-400` : emptyCls}>{marks.TN || "—"}</td>
                          <td className={marks.FN ? `${markBase} text-amber-400` : emptyCls}>{marks.FN || "—"}</td>
                          <td className="px-3 py-2.5 text-xs text-[var(--text-dim)] font-mono">{bucket}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">{fmtNum(r.entry_price)}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums text-[var(--text-dim)]">
                            {fmtNum(r.exit_price)}
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">{fmtNum(r.stop_price)}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">{fmtNum(r.target_t1)}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">{fmtNum(r.target_t2)}</td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                            <PctCell v={r.hypothetical_long_profit_pct_to_t1} />
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                            <PctCell v={r.hypothetical_long_profit_pct_to_t2} />
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                            <PctCell v={r.extension_daily_5d_pct} />
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                            <PctCell v={r.extension_weekly_4w_pct} />
                          </td>
                          <td className="px-3 py-2.5">
                            {r.chase_risk ? (
                              <span
                                className={`rounded-md px-2 py-0.5 text-xs font-semibold capitalize ${
                                  r.chase_risk === "elevated"
                                    ? "bg-red-500/20 text-red-300"
                                    : r.chase_risk === "moderate"
                                      ? "bg-amber-500/20 text-amber-300"
                                      : "bg-emerald-500/15 text-emerald-300"
                                }`}
                                title="Extension guardrail at signal date"
                              >
                                {r.chase_risk}
                              </span>
                            ) : (
                              <span className="text-[var(--text-dim)]">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-[var(--text-dim)] max-w-[140px] truncate" title={r.pattern_name || ""}>
                            {r.pattern_name || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {rows.length === 0 && (
                <p className="p-8 text-center text-[var(--text-dim)] text-sm">
                  No BUY or WATCH rows in this file (or all rows have errors).
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
