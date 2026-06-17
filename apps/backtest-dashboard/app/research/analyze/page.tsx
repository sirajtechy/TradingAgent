"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Database,
  ExternalLink,
  Loader2,
  Microscope,
  RefreshCw,
  XCircle,
} from "lucide-react";

const AGENT_ORDER = [
  "phoenix",
  "fundamental",
  "macro",
  "market_summary",
  "geopolitics",
  "news",
  "insider",
  "sentiment",
] as const;

const AGENT_LABELS: Record<string, string> = {
  phoenix: "Phoenix",
  fundamental: "Fundamental",
  macro: "Macro",
  market_summary: "Market Summary",
  geopolitics: "Geopolitics",
  news: "News",
  insider: "Insider",
  sentiment: "Sentiment",
};

type HeadlineRow = { title?: string; source?: string; date?: string; url?: string; keywords?: string[] };
type InsightRow = { label?: string; value?: string };

type AgentSection = {
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
};

type FusionDoc = {
  orchestrator_score?: number;
  final_signal?: string;
  advisory_verdict?: string;
  note?: string;
  summary?: string;
};

type AnalyzeDoc = {
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

type ApiResponse = {
  ok?: boolean;
  error?: string;
  doc?: AnalyzeDoc;
  ticker?: string;
  as_of_date?: string;
  fusion_mode?: string;
  source?: string;
  cached?: boolean;
  source_file?: string | null;
  source_path?: string | null;
  breakdown_exists?: boolean;
  breakdown_path?: string | null;
};

function defaultYesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function fmtNum(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

function signalColor(signal: string | null | undefined): string {
  const s = String(signal ?? "").toUpperCase();
  if (s === "BUY" || s === "BULLISH") return "text-emerald-300 bg-emerald-500/20 border-emerald-500/30";
  if (s === "WATCH" || s === "NEUTRAL") return "text-amber-300 bg-amber-500/20 border-amber-500/30";
  if (s === "AVOID" || s === "SELL" || s === "BEARISH") return "text-red-300 bg-red-500/20 border-red-500/30";
  return "text-[var(--text-dim)] bg-[var(--bg)] border-[var(--border)]";
}

function scoreColor(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "text-[var(--text-dim)]";
  if (score >= 65) return "text-emerald-300";
  if (score >= 45) return "text-amber-300";
  return "text-red-300";
}

function tierBadge(tier: string | undefined): { label: string; cls: string } {
  if (tier === "primary") return { label: "Primary API", cls: "bg-emerald-500/20 text-emerald-300" };
  if (tier === "fallback") return { label: "Fallback", cls: "bg-amber-500/20 text-amber-300" };
  if (tier === "mixed") return { label: "Mixed", cls: "bg-indigo-500/20 text-indigo-300" };
  return { label: "No data", cls: "bg-[var(--border)] text-[var(--text-dim)]" };
}

function SignalPill({ signal }: { signal?: string | null }) {
  if (!signal) return <span className="text-[var(--text-dim)]">—</span>;
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded border ${signalColor(signal)}`}>
      {signal}
    </span>
  );
}

function AgentSidebarRow({
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

function AgentDetailPanel({ id, agent }: { id: string; agent: AgentSection }) {
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

        {agent.headlines && agent.headlines.length > 0 && (
          <section>
            <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--text-dim)] mb-3">
              Headlines
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

export default function AnalyzeResearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center gap-2 py-16 text-[var(--text-dim)] min-h-screen">
          <Loader2 size={20} className="animate-spin text-indigo-400" />
          Loading…
        </div>
      }
    >
      <AnalyzeResearchContent />
    </Suspense>
  );
}

function AnalyzeResearchContent() {
  const searchParams = useSearchParams();
  const [ticker, setTicker] = useState(searchParams.get("ticker") ?? "");
  const [date, setDate] = useState(searchParams.get("date") ?? defaultYesterday());
  const [fusion, setFusion] = useState(searchParams.get("fusion") ?? "full");
  const [forceRun, setForceRun] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<ApiResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>("phoenix");

  const load = useCallback(
    (opts?: { run?: boolean }) => {
      const tk = ticker.trim().toUpperCase();
      if (!tk) {
        setErr("Enter a ticker symbol");
        return;
      }
      setLoading(true);
      setErr(null);
      const params = new URLSearchParams({ ticker: tk, fusion });
      if (date) params.set("date", date);
      if (opts?.run || forceRun) {
        params.set("source", "run");
        params.set("refresh_context", "1");
      }
      fetch(`/api/analyze?${params}`)
        .then(async (r) => {
          const d = (await r.json()) as ApiResponse;
          if (!r.ok || d.error) {
            throw new Error(d.error ?? "Failed to load analysis");
          }
          setResp(d);
        })
        .catch((e) => {
          setResp(null);
          setErr(e instanceof Error ? e.message : "Failed to load analysis");
        })
        .finally(() => setLoading(false));
    },
    [ticker, date, fusion, forceRun],
  );

  useEffect(() => {
    if (searchParams.get("ticker")) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doc = resp?.doc;
  const fusionDoc = doc?.fusion;
  const agents = doc?.agent_breakdown?.agents ?? {};
  const agentIds = useMemo(() => {
    const fromDoc = Object.keys(agents);
    return AGENT_ORDER.filter((id) => fromDoc.includes(id) || doc?.fusion_mode === "full");
  }, [agents, doc?.fusion_mode]);

  const legitimacy = doc?.agent_breakdown?.data_legitimacy ?? [];
  const fallbackCount = legitimacy.filter((r) => r.source_tier === "fallback").length;
  const primaryCount = legitimacy.filter((r) => r.source_tier === "primary").length;

  const cliHint = `./bin/mts analyze --ticker ${ticker.trim().toUpperCase() || "TICKER"} --date ${date} --fusion ${fusion}${
    fusion === "full" ? " --export-breakdown" : ""
  }`;

  const activeAgent = agents[selectedAgent] ?? { agent_id: selectedAgent, status: "missing" };

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-4 md:px-8">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <Link href="/research" className="text-[var(--text-dim)] hover:text-[var(--text)]">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Microscope size={22} className="text-indigo-400" />
            Deep ticker analyze
          </h1>
        </div>
      </header>

      <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
        <p className="text-sm text-[var(--text-dim)]">
          Full-fusion agent breakdown for a single ticker.{" "}
          <Link href="/research/analyze/watchlist" className="text-indigo-400 hover:text-indigo-300">
            View all BUY/WATCH tickers →
          </Link>
          {" · "}
          CLI: <code className="text-emerald-400/90">{cliHint}</code>
        </p>

        <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
          <form
            className="flex flex-wrap gap-3 items-end"
            onSubmit={(e) => {
              e.preventDefault();
              load({ run: forceRun });
            }}
          >
            <label className="space-y-1">
              <span className="text-xs text-[var(--text-dim)]">Ticker</span>
              <input
                className="block bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm w-28 uppercase"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="KGC"
                required
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-[var(--text-dim)]">As-of date</span>
              <input
                type="date"
                className="block bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-[var(--text-dim)]">Fusion</span>
              <select
                className="block bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm"
                value={fusion}
                onChange={(e) => setFusion(e.target.value)}
              >
                <option value="full">full</option>
                <option value="phoenix-fa">phoenix-fa</option>
                <option value="phoenix">phoenix</option>
                <option value="fundamental">fundamental</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs text-[var(--text-dim)] pb-2">
              <input
                type="checkbox"
                checked={forceRun}
                onChange={(e) => setForceRun(e.target.checked)}
                className="rounded"
              />
              Re-run pipeline (slow)
            </label>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-50"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              Run analysis
            </button>
          </form>
        </section>

        {err && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300 flex items-start gap-2">
            <XCircle size={16} className="shrink-0 mt-0.5" />
            <div>
              <p>{err}</p>
              <p className="text-xs text-red-300/80 mt-1">
                No cached file? Run <code className="text-red-200">{cliHint}</code> or enable re-run.
              </p>
            </div>
          </div>
        )}

        {loading && !doc && (
          <div className="flex items-center justify-center gap-2 py-16 text-[var(--text-dim)]">
            <Loader2 size={20} className="animate-spin text-indigo-400" />
            Loading analysis…
          </div>
        )}

        {doc && (
          <>
            <section className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-[var(--bg-card)] p-6 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-xs text-[var(--text-dim)] uppercase tracking-wide">Ticker</div>
                  <div className="text-3xl font-bold">{doc.ticker ?? resp?.ticker}</div>
                  <div className="text-sm text-[var(--text-dim)] mt-1">
                    {doc.as_of_date ?? resp?.as_of_date} · {doc.fusion_mode ?? fusion}
                    {resp?.cached ? " · cached" : resp?.source === "run" ? " · live run" : ""}
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
                    <div className="text-xs text-[var(--text-dim)]">Orchestrator</div>
                    <div className={`text-2xl font-bold ${scoreColor(fusionDoc?.orchestrator_score)}`}>
                      {fmtNum(fusionDoc?.orchestrator_score, 0)}
                    </div>
                  </div>
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
                    <div className="text-xs text-[var(--text-dim)]">Final signal</div>
                    <div className="mt-1">
                      <SignalPill signal={fusionDoc?.final_signal} />
                    </div>
                  </div>
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/50 px-4 py-3 text-center min-w-[7rem]">
                    <div className="text-xs text-[var(--text-dim)]">Advisory</div>
                    <div className="mt-1">
                      <SignalPill signal={fusionDoc?.advisory_verdict} />
                    </div>
                  </div>
                </div>
              </div>
              {fusionDoc?.note && <p className="text-sm text-[var(--text-dim)] italic">{fusionDoc.note}</p>}
              {resp?.source_path && (
                <p className="text-xs text-[var(--text-dim)]">
                  Source: <code className="text-emerald-400/80">{resp.source_path}</code>
                  {resp.breakdown_exists && resp.breakdown_path && (
                    <>
                      {" · "}
                      Breakdown: <code className="text-indigo-300/80">{resp.breakdown_path}</code>
                    </>
                  )}
                </p>
              )}
            </section>

            {legitimacy.length > 0 && (
              <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4">
                <h2 className="text-sm font-medium flex items-center gap-2 mb-3">
                  <Database size={16} className="text-teal-400" />
                  Data sources
                  <span className="text-[var(--text-dim)] font-normal text-xs">
                    {primaryCount} primary · {fallbackCount} fallback
                  </span>
                </h2>
                <div className="flex flex-wrap gap-2">
                  {legitimacy.map((row) => {
                    const tier = tierBadge(row.source_tier);
                    return (
                      <div
                        key={row.agent_id}
                        className="text-xs rounded-lg border border-[var(--border)] px-2 py-1.5 bg-[var(--bg)]/40"
                      >
                        <span className="font-medium">{AGENT_LABELS[row.agent_id] ?? row.agent_id}</span>
                        <span className={`ml-2 px-1.5 py-0.5 rounded ${tier.cls}`}>{tier.label}</span>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {doc.agent_breakdown && (
              <section className="space-y-3">
                <h2 className="text-sm font-medium flex items-center gap-2">
                  <Brain size={16} className="text-indigo-400" />
                  Agent intelligence
                  <span className="text-[var(--text-dim)] font-normal">
                    ({doc.agent_breakdown.agents_available ?? "?"}/{doc.agent_breakdown.agents_total ?? AGENT_ORDER.length}{" "}
                    available) — select an agent for full breakdown
                  </span>
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-[minmax(240px,320px)_1fr] gap-4">
                  <div className="space-y-2">
                    {agentIds.map((id) => (
                      <AgentSidebarRow
                        key={id}
                        id={id}
                        agent={agents[id] ?? { agent_id: id, status: "missing" }}
                        active={selectedAgent === id}
                        onSelect={() => setSelectedAgent(id)}
                      />
                    ))}
                  </div>
                  <AgentDetailPanel id={selectedAgent} agent={activeAgent} />
                </div>
              </section>
            )}

            {doc.research_digest?.bullets && doc.research_digest.bullets.length > 0 && (
              <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-2">
                <h2 className="text-sm font-medium flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-amber-400" />
                  Combined research narrative
                </h2>
                <pre className="text-sm whitespace-pre-wrap leading-relaxed text-[var(--text)]/90 font-sans">
                  {doc.research_digest.bullets.join("\n\n")}
                </pre>
              </section>
            )}

            {doc.strategies && (
              <section className="rounded-lg border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-2">
                <h2 className="text-sm font-medium">Strategies</h2>
                <pre className="text-xs overflow-x-auto text-[var(--text-dim)] bg-[var(--bg)] p-3 rounded border border-[var(--border)]">
                  {JSON.stringify(doc.strategies, null, 2)}
                </pre>
              </section>
            )}

            {doc.error && (
              <p className="text-red-400 text-sm flex items-center gap-2">
                <XCircle size={14} />
                {doc.error}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
