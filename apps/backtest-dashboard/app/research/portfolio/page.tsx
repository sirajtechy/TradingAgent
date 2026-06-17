"use client";

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import { ArrowLeft, ChevronDown, ChevronRight, LineChart, Wallet } from "lucide-react";

type RunItem = { id: string; run_id: string; modified: string };

type SummaryDoc = {
  run_id?: string;
  start_date?: string;
  end_date?: string;
  summary?: {
    initial_budget?: number;
    final_value?: number;
    total_return_pct?: number;
    cagr_pct?: number;
    max_drawdown_pct?: number;
    sharpe_ratio?: number;
    trade_count?: number;
    regime_cash_rebalances?: number;
  };
  monthly_returns?: { month: string; portfolio_value: number; return_pct: number | null }[];
  warnings?: string[];
};

type HoldingRow = {
  ticker: string;
  sector: string;
  rank: number;
  conviction_score: number;
  momentum_score: number;
  allocation_usd: number;
  shares: number;
  price: number | null;
  attribution?: { rs_rank?: number | null; as_of?: string };
  components?: Record<string, number>;
  breakdown_exists?: boolean;
  breakdown_path?: string | null;
};

type AllocationDoc = {
  as_of?: string;
  budget?: number;
  num_stocks?: number;
  universe_mode?: string;
  source_file?: string;
  source_path?: string;
  holdings?: HoldingRow[];
  error?: string;
};

function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

function fmtUsd(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function phoenixFusion(row: HoldingRow): number {
  return row.components?.conv_phoenix_fusion_score ?? 50;
}

function isEnriched(row: HoldingRow): boolean {
  return phoenixFusion(row) !== 50;
}

function componentVal(row: HoldingRow, key: string): number | null {
  const v = row.components?.[key];
  return v === undefined ? null : v;
}

export default function PortfolioResearchPage() {
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selected, setSelected] = useState("");
  const [doc, setDoc] = useState<SummaryDoc | null>(null);
  const [alloc, setAlloc] = useState<AllocationDoc | null>(null);
  const [allocErr, setAllocErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/portfolio")
      .then((r) => r.json())
      .then((d) => {
        setRuns(d.runs ?? []);
        if (d.runs?.length) setSelected(d.runs[0].run_id);
      })
      .catch(() => setErr("Failed to list portfolio backtests"));
  }, []);

  useEffect(() => {
    fetch("/api/portfolio/allocation")
      .then(async (r) => {
        const d = await r.json();
        if (!r.ok) {
          setAllocErr(d.error ?? "No allocation book found");
          setAlloc(null);
          return;
        }
        setAlloc(d);
        setAllocErr(null);
      })
      .catch(() => setAllocErr("Failed to load allocation book"));
  }, []);

  useEffect(() => {
    if (!selected) {
      setDoc(null);
      return;
    }
    fetch(`/api/portfolio?run=${encodeURIComponent(selected)}`)
      .then((r) => r.json())
      .then((d) => setDoc(d.summary ?? null))
      .catch(() => setErr("Failed to load run"));
  }, [selected]);

  const s = doc?.summary ?? {};
  const holdings = alloc?.holdings ?? [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/research" className="text-[var(--text-dim)] hover:text-[var(--text)]">
          <ArrowLeft size={18} />
        </Link>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Wallet size={22} className="text-emerald-400" />
          Portfolio intelligence
        </h1>
      </div>

      <p className="text-sm text-[var(--text-dim)]">
        Backtest:{" "}
        <code className="text-emerald-400/90">./bin/mts portfolio backtest --start 2024-01-01 --end YYYY-MM-DD</code>
        {" · "}
        Live book:{" "}
        <code className="text-emerald-400/90">./bin/mts portfolio allocate --budget 200000 --full-agents</code>
      </p>

      {err && <p className="text-red-400 text-sm">{err}</p>}

      <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-medium">Current allocation book</h2>
          {alloc?.as_of && (
            <span className="text-xs text-[var(--text-dim)]">
              as of {alloc.as_of}
              {alloc.budget != null && ` · $${fmtUsd(alloc.budget)} budget`}
              {alloc.source_path && (
                <>
                  {" · "}
                  <code className="text-emerald-400/80">{alloc.source_path}</code>
                </>
              )}
            </span>
          )}
        </div>

        {allocErr && (
          <p className="text-amber-400 text-sm">
            {allocErr}. Run{" "}
            <code className="text-emerald-400/90">./bin/mts portfolio allocate --budget 200000</code> then refresh.
          </p>
        )}

        {holdings.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--text-dim)] border-b border-[var(--border)]">
                  <th className="py-2 pr-2 w-8" />
                  <th className="py-2 pr-3">Rank</th>
                  <th className="py-2 pr-3">Ticker</th>
                  <th className="py-2 pr-3">Sector</th>
                  <th className="py-2 pr-3 text-right">Conviction</th>
                  <th className="py-2 pr-3 text-right">Momentum</th>
                  <th className="py-2 pr-3 text-right">Phoenix fusion</th>
                  <th className="py-2 pr-3 text-right">Intel consensus</th>
                  <th className="py-2 pr-3 text-right">Strategy blend</th>
                  <th className="py-2 pr-3 text-right">Alloc USD</th>
                  <th className="py-2 pr-3 text-right">Shares</th>
                  <th className="py-2 pr-3 text-right">Price</th>
                  <th className="py-2">Analysis</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((row) => {
                  const enriched = isEnriched(row);
                  const open = expanded === row.ticker;
                  return (
                    <Fragment key={row.ticker}>
                      <tr
                        className={`border-b border-[var(--border)]/50 ${
                          enriched
                            ? "bg-emerald-500/5 hover:bg-emerald-500/10"
                            : "bg-[var(--bg)]/30 hover:bg-[var(--bg)]/50"
                        }`}
                      >
                        <td className="py-2 pr-2">
                          <button
                            type="button"
                            aria-label={open ? "Collapse" : "Expand"}
                            className="text-[var(--text-dim)] hover:text-[var(--text)]"
                            onClick={() => setExpanded(open ? null : row.ticker)}
                          >
                            {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </button>
                        </td>
                        <td className="py-2 pr-3">{row.rank}</td>
                        <td className="py-2 pr-3 font-medium">{row.ticker}</td>
                        <td className="py-2 pr-3 text-[var(--text-dim)] max-w-[10rem] truncate" title={row.sector}>
                          {row.sector}
                        </td>
                        <td className="py-2 pr-3 text-right">{fmtNum(row.conviction_score)}</td>
                        <td className="py-2 pr-3 text-right">{fmtNum(row.momentum_score, 2)}</td>
                        <td className="py-2 pr-3 text-right">{fmtNum(phoenixFusion(row))}</td>
                        <td className="py-2 pr-3 text-right">
                          {fmtNum(componentVal(row, "conv_intelligence_consensus"))}
                        </td>
                        <td className="py-2 pr-3 text-right">
                          {fmtNum(componentVal(row, "conv_strategy_blend_score"))}
                        </td>
                        <td className="py-2 pr-3 text-right">{fmtUsd(row.allocation_usd)}</td>
                        <td className="py-2 pr-3 text-right">{row.shares ?? "—"}</td>
                        <td className="py-2 pr-3 text-right">{fmtNum(row.price ?? null)}</td>
                        <td className="py-2">
                          <div className="flex flex-col gap-1 items-start">
                            <span
                              className={`inline-block text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${
                                enriched
                                  ? "bg-emerald-500/20 text-emerald-300"
                                  : "bg-[var(--border)] text-[var(--text-dim)]"
                              }`}
                            >
                              {enriched ? "Enriched" : "Momentum only"}
                            </span>
                            <Link
                              href={`/research/analyze?ticker=${encodeURIComponent(row.ticker)}${
                                alloc?.as_of ? `&date=${encodeURIComponent(alloc.as_of)}` : ""
                              }`}
                              className="text-[10px] text-indigo-300/90 hover:text-indigo-200 underline-offset-2 hover:underline"
                            >
                              Deep analyze
                            </Link>
                            {row.breakdown_exists && row.breakdown_path ? (
                              <code className="text-[10px] text-indigo-300/70">{row.breakdown_path}</code>
                            ) : (
                              <span className="text-[10px] text-[var(--text-dim)]">
                                Run:{" "}
                                <code className="text-indigo-300/80">
                                  ./bin/mts analyze --ticker {row.ticker} --fusion full --export-breakdown
                                </code>
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                      {open && (
                        <tr className="border-b border-[var(--border)]/50 bg-[var(--bg)]/40">
                          <td colSpan={13} className="px-4 py-3">
                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
                              {[
                                ["1M return %", componentVal(row, "return_1m")],
                                ["6M return %", componentVal(row, "return_6m")],
                                ["9M return %", componentVal(row, "return_9m")],
                                ["RS rank vs SPY", row.attribution?.rs_rank],
                                ["3M vol %", componentVal(row, "volatility_3m")],
                                ["Momentum raw", componentVal(row, "momentum_raw")],
                              ].map(([label, val]) => (
                                <div key={String(label)}>
                                  <div className="text-[var(--text-dim)]">{label}</div>
                                  <div className="font-medium">{fmtNum(val as number | null, 2)}</div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="flex flex-wrap gap-3 items-center">
        <label className="text-sm text-[var(--text-dim)]">Backtest run</label>
        <select
          className="bg-[var(--bg-card)] border border-[var(--border)] rounded px-3 py-2 text-sm"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {runs.length === 0 && <option value="">No runs yet</option>}
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>
              {r.run_id} ({r.modified.slice(0, 10)})
            </option>
          ))}
        </select>
      </div>

      {doc && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              ["Initial", s.initial_budget?.toLocaleString()],
              ["Final", s.final_value?.toLocaleString()],
              ["Return %", s.total_return_pct],
              ["CAGR %", s.cagr_pct ?? "—"],
              ["Max DD %", s.max_drawdown_pct],
              ["Sharpe", s.sharpe_ratio ?? "—"],
              ["Trades", s.trade_count],
              ["Cash months", s.regime_cash_rebalances],
            ].map(([label, val]) => (
              <div key={String(label)} className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-3">
                <div className="text-xs text-[var(--text-dim)]">{label}</div>
                <div className="text-lg font-medium">{val ?? "—"}</div>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
            <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
              <LineChart size={16} className="text-indigo-400" />
              Month-on-month
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-dim)] border-b border-[var(--border)]">
                    <th className="py-2 pr-4">Month</th>
                    <th className="py-2 pr-4">Value</th>
                    <th className="py-2">Return %</th>
                  </tr>
                </thead>
                <tbody>
                  {(doc.monthly_returns ?? []).map((row) => (
                    <tr key={row.month} className="border-b border-[var(--border)]/50">
                      <td className="py-2 pr-4">{row.month}</td>
                      <td className="py-2 pr-4">{row.portfolio_value?.toLocaleString()}</td>
                      <td className="py-2">{row.return_pct ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {doc.warnings?.length ? (
            <p className="text-amber-400 text-sm">Warnings: {doc.warnings.join("; ")}</p>
          ) : null}
        </>
      )}
    </div>
  );
}
