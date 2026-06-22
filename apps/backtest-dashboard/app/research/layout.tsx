"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Crosshair,
  Grid3X3,
  Home,
  Layers,
  Microscope,
  ShieldCheck,
  ShoppingCart,
  Table2,
  Zap,
} from "lucide-react";

const NAV = [
  { href: "/research/console", label: "Command Center", icon: Zap, color: "text-amber-400" },
  { href: "/research", label: "Overview", icon: Home, exact: true },
  { href: "/research/backtests", label: "Technical backtest", icon: Grid3X3, color: "text-emerald-400" },
  {
    href: "/research/backtests/verify",
    label: "Polygon verify",
    icon: ShieldCheck,
    color: "text-cyan-400",
  },
  { href: "/research/phoenix", label: "Phoenix pilot", icon: Table2, color: "text-indigo-400" },
  { href: "/research/analyze", label: "Deep analyze", icon: Microscope, color: "text-indigo-400" },
  {
    href: "/research/analyze/watchlist",
    label: "BUY/WATCH dive",
    icon: ShoppingCart,
    color: "text-emerald-400",
  },
  { href: "/research/signals", label: "Signals export", icon: Crosshair, color: "text-emerald-400" },
  { href: "/research/portfolio", label: "Portfolio", icon: BarChart3, color: "text-teal-400" },
  { href: "/research/runs", label: "Trading runs", icon: Layers, color: "text-amber-400" },
];

export default function ResearchLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <aside className="w-56 shrink-0 border-r border-[var(--border)] bg-[var(--bg-card)] flex flex-col">
        <div className="p-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm">
              R
            </div>
            <div>
              <div className="font-semibold text-sm">Research Lab</div>
              <div className="text-[10px] text-[var(--text-dim)]">MyTradingSpace</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {NAV.map((item) => {
            let active: boolean;
            if (item.exact) {
              active = pathname === item.href;
            } else if (item.href === "/research/analyze") {
              active = pathname === "/research/analyze";
            } else {
              active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            }
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
        <div className="p-3 border-t border-[var(--border)] text-[10px] text-[var(--text-dim)] space-y-1">
          <div>
            <code className="text-emerald-400/80">Command Center → run all</code>
          </div>
          <div>
            <code className="text-emerald-400/80">./bin/mts daily</code>
          </div>
          <div>
            <code className="text-emerald-400/80">./bin/mts export</code>
          </div>
          <div>
            <code className="text-emerald-400/80">./bin/mts backtest sync</code>
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
