"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Play,
  Terminal,
  XCircle,
  Zap,
} from "lucide-react";

type WorkflowField = {
  id: string;
  label: string;
  type: string;
  default?: string | number | boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  required?: boolean;
  help?: string;
};

type Workflow = {
  id: string;
  category: string;
  title: string;
  description: string;
  cliHint: string;
  longRunning: boolean;
  estimatedMin?: number;
  fields: WorkflowField[];
};

type Category = { id: string; label: string; color: string };

type ResultLink = { label: string; href: string };

type Job = {
  id: string;
  workflowId: string;
  title: string;
  status: "queued" | "running" | "success" | "failed";
  command: string;
  startedAt: string;
  finishedAt?: string;
  exitCode?: number | null;
  logTail?: string;
  resultLinks: ResultLink[];
  error?: string;
};

const CATEGORY_STYLES: Record<string, string> = {
  daily: "border-emerald-500/30 bg-emerald-500/5",
  backtest: "border-indigo-500/30 bg-indigo-500/5",
  analyze: "border-violet-500/30 bg-violet-500/5",
  agents: "border-amber-500/30 bg-amber-500/5",
  system: "border-zinc-500/30 bg-zinc-500/5",
};

const QUICK_IDS = ["daily", "backtest_sync", "export_signals", "analyze_watchlist"];

function defaultValues(fields: WorkflowField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.default !== undefined) out[f.id] = f.default;
    else if (f.type === "checkbox") out[f.id] = false;
    else out[f.id] = "";
  }
  return out;
}

function JobStatusBadge({ status }: { status: Job["status"] }) {
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-sky-300">
        <Loader2 size={12} className="animate-spin" /> Running
      </span>
    );
  }
  if (status === "success") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
        <CheckCircle2 size={12} /> Done
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-400">
        <XCircle size={12} /> Failed
      </span>
    );
  }
  return <span className="text-xs text-[var(--text-dim)]">{status}</span>;
}

function WorkflowCard({
  workflow,
  onRun,
  running,
}: {
  workflow: Workflow;
  onRun: (id: string, params: Record<string, unknown>) => void;
  running: boolean;
}) {
  const [params, setParams] = useState<Record<string, unknown>>(() => defaultValues(workflow.fields));
  const style = CATEGORY_STYLES[workflow.category] ?? CATEGORY_STYLES.system;

  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-3 ${style}`}>
      <div>
        <h3 className="font-semibold text-sm">{workflow.title}</h3>
        <p className="text-xs text-[var(--text-dim)] mt-1 leading-relaxed">{workflow.description}</p>
        <code className="text-[10px] text-emerald-400/70 mt-2 block truncate">{workflow.cliHint}</code>
      </div>

      {workflow.fields.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {workflow.fields.map((field) => (
            <label key={field.id} className="flex flex-col gap-1 text-xs">
              <span className="text-[var(--text-dim)]">
                {field.label}
                {field.required && <span className="text-red-400"> *</span>}
              </span>
              {field.type === "checkbox" ? (
                <input
                  type="checkbox"
                  checked={Boolean(params[field.id])}
                  onChange={(e) => setParams((p) => ({ ...p, [field.id]: e.target.checked }))}
                  className="w-4 h-4 accent-emerald-500"
                />
              ) : field.type === "select" ? (
                <select
                  className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1.5 text-sm"
                  value={String(params[field.id] ?? "")}
                  onChange={(e) => setParams((p) => ({ ...p, [field.id]: e.target.value }))}
                >
                  {!field.required && <option value="">—</option>}
                  {(field.options ?? []).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : field.type === "number" ? (
                <input
                  type="number"
                  className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1.5 text-sm"
                  placeholder={field.placeholder}
                  value={params[field.id] === "" ? "" : String(params[field.id] ?? "")}
                  onChange={(e) =>
                    setParams((p) => ({
                      ...p,
                      [field.id]: e.target.value === "" ? "" : Number(e.target.value),
                    }))
                  }
                />
              ) : (
                <input
                  type={field.type === "date" ? "date" : "text"}
                  className="bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1.5 text-sm"
                  placeholder={field.placeholder}
                  value={String(params[field.id] ?? "")}
                  onChange={(e) => setParams((p) => ({ ...p, [field.id]: e.target.value }))}
                />
              )}
              {field.help && <span className="text-[10px] text-[var(--text-dim)]">{field.help}</span>}
            </label>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-auto pt-1">
        {workflow.longRunning && (
          <span className="text-[10px] text-[var(--text-dim)]">~{workflow.estimatedMin ?? "?"} min</span>
        )}
        <button
          type="button"
          disabled={running}
          onClick={() => onRun(workflow.id, params)}
          className="ml-auto inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-3 py-1.5 text-sm font-medium text-white transition-colors"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Run
        </button>
      </div>
    </div>
  );
}

export default function CommandCenterPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("daily");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [completedBanner, setCompletedBanner] = useState<Job | null>(null);

  const loadCatalog = useCallback(() => {
    fetch("/api/control/catalog")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) throw new Error(d.error);
        setCategories(d.categories ?? []);
        setWorkflows(d.workflows ?? []);
      })
      .catch((e) => setErr(e.message));
  }, []);

  const loadJobs = useCallback(() => {
    fetch("/api/control/jobs")
      .then((r) => r.json())
      .then((d) => setJobs(d.jobs ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadCatalog();
    loadJobs();
  }, [loadCatalog, loadJobs]);

  // Poll active job
  useEffect(() => {
    if (!activeJobId) return;
    const poll = () => {
      fetch(`/api/control/jobs/${activeJobId}`)
        .then((r) => r.json())
        .then((d) => {
          if (!d.job) return;
          const job = d.job as Job;
          setJobs((prev) => {
            const rest = prev.filter((j) => j.id !== job.id);
            return [job, ...rest];
          });
          if (job.status === "running") return;
          setRunningIds((s) => {
            const n = new Set(s);
            n.delete(job.workflowId);
            return n;
          });
          if (job.status === "success") {
            setCompletedBanner(job);
            if (job.resultLinks?.length === 1) {
              router.push(job.resultLinks[0].href);
            }
          }
        })
        .catch(() => {});
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [activeJobId, router]);

  const runWorkflow = async (workflowId: string, params: Record<string, unknown>) => {
    setErr(null);
    setCompletedBanner(null);
    setRunningIds((s) => new Set(s).add(workflowId));
    try {
      const r = await fetch("/api/control/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflowId, params }),
      });
      const d = await r.json();
      if (!d.ok) throw new Error(d.error || "Start failed");
      const job = d.job as Job;
      setActiveJobId(job.id);
      setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)]);
    } catch (e) {
      setRunningIds((s) => {
        const n = new Set(s);
        n.delete(workflowId);
        return n;
      });
      setErr(e instanceof Error ? e.message : "Run failed");
    }
  };

  const filtered = useMemo(
    () => workflows.filter((w) => w.category === activeCategory),
    [workflows, activeCategory],
  );

  const quickWorkflows = useMemo(
    () => QUICK_IDS.map((id) => workflows.find((w) => w.id === id)).filter(Boolean) as Workflow[],
    [workflows],
  );

  const activeJob = jobs.find((j) => j.id === activeJobId) ?? jobs[0];

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6 pb-24">
      <header className="flex flex-wrap items-start gap-4">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Zap className="text-amber-400" size={24} />
            Command Center
          </h1>
          <p className="text-sm text-[var(--text-dim)] mt-1 max-w-2xl">
            Run every <code className="text-emerald-400/90">./bin/mts</code> workflow from one place.
            When a job finishes, use the result links to jump straight to the right dashboard page.
          </p>
        </div>
      </header>

      {err && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </div>
      )}

      {completedBanner && completedBanner.status === "success" && (
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 flex flex-wrap items-center gap-3">
          <CheckCircle2 className="text-emerald-400 shrink-0" size={20} />
          <div className="flex-1 min-w-[200px]">
            <div className="font-medium text-emerald-200">{completedBanner.title} completed</div>
            <div className="text-xs text-[var(--text-dim)] mt-0.5">Open results:</div>
          </div>
          <div className="flex flex-wrap gap-2">
            {completedBanner.resultLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-500"
              >
                {link.label}
                <ArrowRight size={14} />
              </Link>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setCompletedBanner(null)}
            className="text-xs text-[var(--text-dim)] hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      <section>
        <h2 className="text-xs uppercase tracking-wide text-[var(--text-dim)] mb-3">Quick actions</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {quickWorkflows.map((w) => (
            <WorkflowCard
              key={w.id}
              workflow={w}
              onRun={runWorkflow}
              running={runningIds.has(w.id)}
            />
          ))}
        </div>
      </section>

      <section>
        <div className="flex flex-wrap gap-2 mb-4">
          {categories.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setActiveCategory(c.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                activeCategory === c.id
                  ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-200"
                  : "border-[var(--border)] text-[var(--text-dim)] hover:text-white"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {filtered.map((w) => (
            <WorkflowCard
              key={w.id}
              workflow={w}
              onRun={runWorkflow}
              running={runningIds.has(w.id)}
            />
          ))}
        </div>
      </section>

      {/* Job panel — fixed bottom */}
      <div className="fixed bottom-0 left-56 right-0 border-t border-[var(--border)] bg-[var(--bg-card)]/95 backdrop-blur z-10">
        <div className="max-w-[1400px] mx-auto px-6 py-3 grid lg:grid-cols-[280px_1fr] gap-4">
          <div>
            <div className="text-xs uppercase text-[var(--text-dim)] mb-2 flex items-center gap-2">
              <Terminal size={12} /> Recent jobs
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1 max-h-24">
              {jobs.slice(0, 8).map((j) => (
                <button
                  key={j.id}
                  type="button"
                  onClick={() => setActiveJobId(j.id)}
                  className={`shrink-0 rounded-lg border px-2 py-1.5 text-left text-xs min-w-[140px] ${
                    activeJobId === j.id ? "border-emerald-500/50 bg-emerald-500/10" : "border-[var(--border)]"
                  }`}
                >
                  <div className="truncate font-medium">{j.title}</div>
                  <JobStatusBadge status={j.status} />
                </button>
              ))}
              {!jobs.length && (
                <span className="text-xs text-[var(--text-dim)]">No jobs yet — run a workflow above.</span>
              )}
            </div>
          </div>
          {activeJob && (
            <div className="min-h-[80px]">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <JobStatusBadge status={activeJob.status} />
                <code className="text-[10px] text-[var(--text-dim)] truncate flex-1">{activeJob.command}</code>
                {activeJob.status === "success" &&
                  activeJob.resultLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="text-xs text-emerald-400 hover:underline inline-flex items-center gap-1"
                    >
                      {link.label} <ArrowRight size={10} />
                    </Link>
                  ))}
              </div>
              <pre className="text-[10px] font-mono text-[var(--text-dim)] max-h-20 overflow-auto whitespace-pre-wrap bg-black/30 rounded p-2">
                {activeJob.logTail || "(waiting for output…)"}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
