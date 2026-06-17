"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  ChevronLeft,
  Crosshair,
  Layers,
  Microscope,
  ShoppingCart,
  Table2,
} from "lucide-react";

const NAV = [
  { href: "/research/signals", label: "Signals", icon: Crosshair, color: "text-emerald-400" },
  { href: "/research/phoenix", label: "Phoenix pilot", icon: Table2, color: "text-indigo-400" },
  { href: "/research/portfolio", label: "Portfolio", icon: BarChart3, color: "text-teal-400" },
  { href: "/research/analyze", label: "Deep analyze", icon: Microscope, color: "text-indigo-400" },
  { href: "/research/analyze/watchlist", label: "BUY/WATCH dive", icon: ShoppingCart, color: "text-emerald-400" },
  { href: "/research/runs", label: "Trading runs", icon: Layers, color: "text-amber-400" },
  { href: "/research/scans", label: "Phoenix scans", icon: BarChart3, color: "text-purple-400" },
];

export default function ResearchLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--text)]">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-[var(--border)] bg-[var(--bg-card)] flex flex-col">
        <div className="p-4 border-b border-[var(--border)]">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-[var(--text-dim)] hover:text-[var(--text)]"
          >
            <ChevronLeft size={16} />
            Back to Dashboard
          </Link>
        </div>
        <div className="p-3">
          <Link href="/research" className="block px-3 py-2 mb-2 rounded-lg font-medium text-lg">
            Research Lab
          </Link>
          <nav className="space-y-1">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    active
                      ? "bg-emerald-500/10 text-emerald-300"
                      : "text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--bg)]"
                  }`}
                >
                  <item.icon size={16} className={active ? "text-emerald-400" : item.color} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="mt-auto p-4 border-t border-[var(--border)] text-xs text-[var(--text-dim)]">
          Refresh: <code className="text-emerald-400/80">./bin/mts export</code>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
