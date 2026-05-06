import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

function getMyTradingSpaceRoot(): string {
  // process.cwd() is .../MyTradingSpace/backtest-dashboard
  return path.resolve(process.cwd(), "..");
}

function getScanRoot(): string {
  return path.join(getMyTradingSpaceRoot(), "data", "output", "phoenix_sector_scans");
}

function isIsoDateDir(name: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(name);
}

export async function GET() {
  try {
    const scanRoot = getScanRoot();
    if (!fs.existsSync(scanRoot)) {
      return NextResponse.json({ runs: [] }, { headers: { "Cache-Control": "no-store" } });
    }

    const dirs = fs
      .readdirSync(scanRoot, { withFileTypes: true })
      .filter((d) => d.isDirectory() && isIsoDateDir(d.name))
      .map((d) => d.name)
      .sort((a, b) => b.localeCompare(a)); // newest first

    // Try to read per-run meta quickly (small header). If anything fails, still return the date.
    const runs = dirs.map((date) => {
      const file = path.join(scanRoot, date, `phoenix_sector_scan_${date}.json`);
      if (!fs.existsSync(file)) return { date, hasFile: false };
      try {
        const raw = fs.readFileSync(file, "utf-8");
        const parsed = JSON.parse(raw);
        const meta = parsed?.meta ?? {};
        return {
          date,
          hasFile: true,
          sectors: meta.sectors ?? [],
          tickers: meta.tickers_requested ?? meta.results ?? null,
          elapsed_sec: meta.elapsed_sec ?? null,
          generated_at: meta.generated_at ?? null,
        };
      } catch {
        return { date, hasFile: true };
      }
    });

    return NextResponse.json({ runs }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ runs: [] }, { status: 500 });
  }
}

