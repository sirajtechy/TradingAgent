"use client";

import { BarChart3, Crosshair, Layers, Table2 } from "lucide-react";
import Link from "next/link";

const CARDS = [
  {
    href: "/research/signals",
    title: "Signal reconciliation",
    desc: "Deduped BUY & WATCH across all sector runs and dates",
    icon: <Crosshair className="text-emerald-400" size={22} />,
  },
  {
    href: "/research/phoenix",
    title: "Phoenix WATCH / BUY",
    desc: "Single master_pilot run — sortable table & Excel",
    icon: <Table2 className="text-indigo-400" size={22} />,
  },
  {
    href: "/research/runs",
    title: "Trading runs",
    desc: "Browse run_bundle & master_pilot artifacts, compare runs",
    icon: <Layers className="text-amber-400" size={22} />,
  },
  {
    href: "/research/scans",
    title: "Phoenix scans",
    desc: "Sector scan exports",
    icon: <BarChart3 className="text-purple-400" size={22} />,
  },
];

export default function ResearchHubPage() {
  return (
    <div className="p-6 md:p-10">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Research Lab</h1>
        <p className="text-[var(--text-dim)] mb-8 max-w-xl">
          Backtest exploration — signals, runs, and Phoenix pilots. Refresh data with{" "}
          <code className="text-emerald-400/90">./bin/mts export</code>.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {CARDS.map((c) => (
            <Link
              key={c.href}
              href={c.href}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 hover:border-emerald-500/40 transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5">{c.icon}</span>
                <div>
                  <h2 className="font-medium text-[var(--text)]">{c.title}</h2>
                  <p className="text-sm text-[var(--text-dim)] mt-1">{c.desc}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
