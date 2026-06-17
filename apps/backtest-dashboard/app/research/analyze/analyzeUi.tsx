"use client";

import { AlertTriangle, ExternalLink, XCircle } from "lucide-react";

export const AGENT_ORDER = [
  "phoenix",
  "fundamental",
  "macro",
  "market_summary",
  "geopolitics",
  "news",
  "insider",
  "sentiment",
] as const;

export const AGENT_LABELS: Record<string, string> = {
  phoenix: "Phoenix",
  fundamental: "Fundamental",
  macro: "Macro",
  market_summary: "Market Summary",
  geopolitics: "Geopolitics",
  news: "News",
  insider: "Insider",
  sentiment: "Sentiment",
};

export type HeadlineRow = { title?: string; source?: string; date?: string; url?: string; keywords?: string[] };
export type InsightRow = { label?: string; value?: string };
export type InsiderSaleRow = {
  owner?: string;
  title?: string;
  shares?: number;
  dollars?: number;
  avg_price?: number;
  sale_count?: number;
  first_sale_date?: string;
  last_sale_date?: string;
  sale_period?: string;
};
export type RecentTradeRow = {
  owner?: string;
  title?: string;
  type?: string;
  shares?: number;
  value?: number;
  price?: number | null;
  date?: string;
};

export type AgentSection = {
  agent_id?: string;
  status?: string;
  signal?: string | null;
  score?: number | null;
  band?: string | null;
  confidence?: string | null;
  bullets?: string[];
  warnings?: string[];
  error?: string | null;
  report?: string | null;
  one_liner?: string;
  insights?: InsightRow[];
  headlines?: HeadlineRow[];
  data_sources?: string[];
  source_tier?: string;
  data_quality?: string;
  phoenix_signal?: string;
  stage?: string;
  pattern?: string;
  sentiment_label?: string;
  market_wide_signal?: string;
  vix?: number;
  vix_regime?: string;
  sector_leaders?: { ticker?: string; label?: string; vs_spy_20d_pct?: number }[];
  sector_laggards?: { ticker?: string; label?: string; vs_spy_20d_pct?: number }[];
  macro_metrics?: Record<string, unknown>;
  geo_headline_count?: number;
  per_insider_sales?: InsiderSaleRow[];
  recent_trades?: RecentTradeRow[];
  metrics?: {
    sell_value?: number;
    total_shares_sold?: number;
    avg_sale_price?: number;
    sell_count?: number;
    first_sale_date?: string;
    last_sale_date?: string;
  };
};

export type FusionDoc = {
  orchestrator_score?: number;
  final_signal?: string;
  advisory_verdict?: string;
  note?: string;
  summary?: string;
};

export type AnalyzeDoc = {
  ok?: boolean;
  fusion_mode?: string;
  ticker?: string;
  as_of_date?: string;
  fusion?: FusionDoc;
  agent_breakdown?: {
    agents?: Record<string, AgentSection>;
    agents_available?: number;
    agents_total?: number;
    note?: string;
    data_legitimacy?: { agent_id: string; source_tier?: string; data_sources?: string[]; data_quality?: string }[];
  };
  phoenix?: Record<string, unknown>;
  fundamental?: Record<string, unknown>;
  research_digest?: { bullets?: string[]; sentiment?: string; confidence?: string };
  strategies?: Record<string, unknown>;
  error?: string;
};

export function defaultYesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

export function fmtNum(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

export function fmtMoney(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `$${Number(v).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function fmtShares(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function fmtShortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function fmtDateRange(first?: string, last?: string): string {
  if (!first && !last) return "—";
  if (!last || first === last) return fmtShortDate(first ?? last);
  if (!first) return fmtShortDate(last);
  return `${fmtShortDate(first)} – ${fmtShortDate(last)}`;
}

export function signalColor(signal: string | null | undefined): string {
  const s = String(signal ?? "").toUpperCase();
  if (s === "BUY" || s === "BULLISH") return "text-emerald-300 bg-emerald-500/20 border-emerald-500/30";
  if (s === "WATCH" || s === "NEUTRAL") return "text-amber-300 bg-amber-500/20 border-amber-500/30";
  if (s === "AVOID" || s === "SELL" || s === "BEARISH") return "text-red-300 bg-red-500/20 border-red-500/30";
  return "text-[var(--text-dim)] bg-[var(--bg)] border-[var(--border)]";
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "text-[var(--text-dim)]";
  if (score >= 65) return "text-emerald-300";
  if (score >= 45) return "text-amber-300";
  return "text-red-300";
}

export function tierBadge(tier: string | undefined): { label: string; cls: string } {
  if (tier === "primary") return { label: "Primary API", cls: "bg-emerald-500/20 text-emerald-300" };
  if (tier === "derived") return { label: "Derived", cls: "bg-purple-500/20 text-purple-300" };
  if (tier === "fallback") return { label: "Fallback", cls: "bg-amber-500/20 text-amber-300" };
  if (tier === "mixed") return { label: "Mixed", cls: "bg-indigo-500/20 text-indigo-300" };
  return { label: "No data", cls: "bg-[var(--border)] text-[var(--text-dim)]" };
}

export function SignalPill({ signal }: { signal?: string | null }) {
  if (!signal) return <span className="text-[var(--text-dim)]">—</span>;
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded border ${signalColor(signal)}`}>
      {signal}
    </span>
  );
}

export function AgentSidebarRow({
  id,
  agent,
  active,
  onSelect,
}: {
  id: string;
  agent: AgentSection;
  active: boolean;
  onSelect: () => void;
}) {
  const tier = tierBadge(agent.source_tier);
  const displaySignal =
    agent.signal ?? agent.phoenix_signal ?? agent.market_wide_signal ?? agent.sentiment_label;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left rounded-lg border p-3 transition-colors ${
        active
          ? "border-indigo-500/50 bg-indigo-500/10"
          : "border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg)]/80"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-sm font-medium">{AGENT_LABELS[id] ?? id}</span>
        <span className={`text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded ${tier.cls}`}>
          {tier.label}
        </span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <SignalPill signal={displaySignal} />
        <span className={`text-xs font-medium ${scoreColor(agent.score ?? null)}`}>
          {fmtNum(agent.score, 0)}
        </span>
      </div>
      <p className="text-xs text-[var(--text-dim)] leading-relaxed line-clamp-3">
        {agent.one_liner ?? agent.bullets?.[0] ?? "No summary available."}
      </p>
    </button>
  );
}

export function AgentDetailPanel({ id, agent }: { id: string; agent: AgentSection }) {
  const tier = tierBadge(agent.source_tier);
  const displaySignal =
    agent.signal ?? agent.phoenix_signal ?? agent.market_wide_signal ?? agent.sentiment_label;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
      <div className="border-b border-[var(--border)] p-5 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">{AGENT_LABELS[id] ?? id}</h3>
            <p className="text-sm text-[var(--text)]/90 mt-2 leading-relaxed">
              {agent.one_liner ?? "No one-line summary for this agent."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <SignalPill signal={displaySignal} />
            <span className={`text-lg font-bold ${scoreColor(agent.score ?? null)}`}>
              {fmtNum(agent.score, 0)}
            </span>
            <span className={`text-[10px] uppercase tracking-wide px-2 py-1 rounded ${tier.cls}`}>
              {tier.label}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-[var(--text-dim)]">
          {agent.band && <span>Band: <strong className="text-[var(--text)]">{agent.band}</strong></span>}
          {agent.confidence && (
            <span>Confidence: <strong className="text-[var(--text)]">{agent.confidence}</strong></span>
          )}
          {agent.data_quality && (
            <span>Quality: <strong className="text-[var(--text)]">{agent.data_quality}</strong></span>
          )}
          {agent.phoenix_signal && (
            <span>Phoenix native: <strong className="text-[var(--text)]">{agent.phoenix_signal}</strong></span>
          )}
        </div>

        {agent.data_sources && agent.data_sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {agent.data_sources.map((src) => (
              <code
                key={src}
                className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg)] border border-[var(--border)] text-emerald-400/90"
              >
                {src}
              </code>
            ))}
          </div>
        )}
      </div>

      <div className="p-5 space-y-6">
        {agent.bullets && agent.bullets.length > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Key insights
            </h4>
            <div className="space-y-3">
              {agent.bullets.map((b, i) => (
                <p key={i} className="text-sm leading-relaxed border-l-2 border-indigo-500/40 pl-3">
                  {b}
                </p>
              ))}
            </div>
          </section>
        )}

        {agent.insights && agent.insights.length > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Metrics &amp; details
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {agent.insights.map((row, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 px-3 py-2 text-sm"
                >
                  <div className="text-[var(--text-dim)] text-xs">{row.label}</div>
                  <div className="font-medium">{row.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {id === "insider" && (agent.per_insider_sales?.length ?? 0) > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Who sold (Form 4 code S)
            </h4>
            <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bg)]/60 text-[var(--text-dim)] text-xs uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium">Insider</th>
                    <th className="text-left px-3 py-2 font-medium">When</th>
                    <th className="text-right px-3 py-2 font-medium">Sales</th>
                    <th className="text-right px-3 py-2 font-medium">Shares</th>
                    <th className="text-right px-3 py-2 font-medium">Avg price</th>
                    <th className="text-right px-3 py-2 font-medium">Total sold</th>
                  </tr>
                </thead>
                <tbody>
                  {agent.per_insider_sales!.map((row, i) => (
                    <tr key={i} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2">
                        <div className="font-medium">{row.owner ?? "Unknown"}</div>
                        {row.title && (
                          <div className="text-xs text-[var(--text-dim)]">{row.title}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs sm:text-sm whitespace-nowrap">
                        {fmtDateRange(row.first_sale_date, row.last_sale_date)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">{row.sale_count ?? "—"}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtShares(row.shares)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtMoney(row.avg_price, 2)}</td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium">
                        {fmtMoney(row.dollars, 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                {agent.metrics?.sell_value != null && (
                  <tfoot className="border-t border-[var(--border)] bg-[var(--bg)]/40 text-xs">
                    <tr>
                      <td className="px-3 py-2 font-medium">All insiders</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {fmtDateRange(agent.metrics.first_sale_date, agent.metrics.last_sale_date)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium">
                        {agent.metrics.sell_count ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium">
                        {fmtShares(agent.metrics.total_shares_sold)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium">
                        {fmtMoney(agent.metrics.avg_sale_price, 2)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums font-medium">
                        {fmtMoney(agent.metrics.sell_value, 0)}
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </section>
        )}

        {id === "insider" && (agent.recent_trades?.length ?? 0) > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Recent individual sales
            </h4>
            <ul className="space-y-2">
              {agent.recent_trades!.slice(0, 10).map((trade, i) => (
                <li
                  key={i}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border)] bg-[var(--bg)]/30 px-3 py-2 text-sm"
                >
                  <div>
                    <div className="font-medium">{trade.owner ?? "Insider"}</div>
                    {trade.title && (
                      <div className="text-xs text-[var(--text-dim)]">{trade.title}</div>
                    )}
                  </div>
                  <div className="text-right text-xs sm:text-sm tabular-nums">
                    <div className="font-medium text-[var(--text)]">
                      {fmtShortDate(trade.date)}
                    </div>
                    <div>
                      {fmtShares(trade.shares)} sh @ {fmtMoney(trade.price, 2)}
                    </div>
                    <div className="text-[var(--text-dim)]">{fmtMoney(trade.value, 0)}</div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {agent.headlines && agent.headlines.length > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Headlines ({agent.headlines.length})
            </h4>
            <ul className="space-y-3">
              {agent.headlines.map((h, i) => (
                <li key={i} className="text-sm border border-[var(--border)] rounded-lg p-3 bg-[var(--bg)]/30">
                  <div className="font-medium leading-snug">{h.title ?? "Untitled"}</div>
                  <div className="text-xs text-[var(--text-dim)] mt-1 flex flex-wrap gap-2">
                    {h.source && <span>{h.source}</span>}
                    {h.date && <span>{h.date}</span>}
                    {h.keywords && h.keywords.length > 0 && (
                      <span className="text-amber-400/90">{h.keywords.join(", ")}</span>
                    )}
                  </div>
                  {h.url && (
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 mt-2"
                    >
                      Read <ExternalLink size={12} />
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {agent.report && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Full agent report
            </h4>
            <pre className="text-xs whitespace-pre-wrap leading-relaxed text-[var(--text)]/90 bg-[var(--bg)] border border-[var(--border)] rounded-lg p-4 font-sans">
              {agent.report}
            </pre>
          </section>
        )}

        {agent.warnings && agent.warnings.length > 0 && (
          <div className="text-xs text-amber-400 space-y-1">
            {agent.warnings.map((w, i) => (
              <div key={i} className="flex items-start gap-1">
                <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                {w}
              </div>
            ))}
          </div>
        )}

        {agent.error && (
          <p className="text-xs text-red-400 flex items-start gap-1">
            <XCircle size={12} className="shrink-0 mt-0.5" />
            {agent.error}
          </p>
        )}
      </div>
    </div>
  );
}

export function AnalyzeAgentGrid({
  doc,
  selectedAgent,
  onSelectAgent,
}: {
  doc: AnalyzeDoc;
  selectedAgent: string;
  onSelectAgent: (id: string) => void;
}) {
  const agents = doc.agent_breakdown?.agents ?? {};
  const agentIds = AGENT_ORDER.filter(
    (id) => agents[id] || doc.fusion_mode === "full",
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(240px,320px)_1fr] gap-4">
      <div className="space-y-2">
        {agentIds.map((id) => (
          <AgentSidebarRow
            key={id}
            id={id}
            agent={agents[id] ?? { agent_id: id, status: "missing" }}
            active={selectedAgent === id}
            onSelect={() => onSelectAgent(id)}
          />
        ))}
      </div>
      <AgentDetailPanel id={selectedAgent} agent={agents[selectedAgent] ?? { agent_id: selectedAgent, status: "missing" }} />
    </div>
  );
}

export function FusionHero({
  doc,
  fusion,
  meta,
}: {
  doc: AnalyzeDoc;
  fusion?: FusionDoc;
  meta?: { cached?: boolean; source?: string; source_path?: string | null; breakdown_path?: string | null; breakdown_exists?: boolean };
}) {
  return (
    <section className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-[var(--bg-card)] p-6 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs text-[var(--text-dim)] uppercase tracking-wide">Ticker</div>
          <div className="text-3xl font-bold">{doc.ticker}</div>
          <div className="text-sm text-[var(--text-dim)] mt-1">
            {doc.as_of_date} · {doc.fusion_mode}
            {meta?.cached ? " · cached" : meta?.source === "run" ? " · live run" : ""}
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
            <div className="text-xs text-[var(--text-dim)]">Orchestrator</div>
            <div className={`text-2xl font-bold ${scoreColor(fusion?.orchestrator_score)}`}>
              {fmtNum(fusion?.orchestrator_score, 0)}
            </div>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
            <div className="text-xs text-[var(--text-dim)]">Final signal</div>
            <div className="mt-1">
              <SignalPill signal={fusion?.final_signal} />
            </div>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
            <div className="text-xs text-[var(--text-dim)]">Advisory</div>
            <div className="mt-1">
              <SignalPill signal={fusion?.advisory_verdict} />
            </div>
          </div>
        </div>
      </div>
      {fusion?.note && <p className="text-sm text-[var(--text-dim)] italic">{fusion.note}</p>}
      {meta?.source_path && (
        <p className="text-xs text-[var(--text-dim)]">
          Source: <code className="text-emerald-400/80">{meta.source_path}</code>
        </p>
      )}
    </section>
  );
}
