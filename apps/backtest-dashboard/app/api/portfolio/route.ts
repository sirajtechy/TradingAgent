import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

type RunItem = {
  id: string;
  run_id: string;
  relPath: string;
  modified: string;
};

function listRuns(root: string): RunItem[] {
  const scanRoot = path.join(root, "data", "output", "portfolio_backtests");
  if (!fs.existsSync(scanRoot)) return [];
  const found: RunItem[] = [];
  for (const ent of fs.readdirSync(scanRoot, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue;
    const summaryPath = path.join(scanRoot, ent.name, "summary.json");
    if (!fs.existsSync(summaryPath)) continue;
    const st = fs.statSync(summaryPath);
    found.push({
      id: encodeURIComponent(ent.name),
      run_id: ent.name,
      relPath: path.relative(root, summaryPath).replace(/\\/g, "/"),
      modified: new Date(st.mtimeMs).toISOString(),
    });
  }
  return found.sort((a, b) => (a.modified < b.modified ? 1 : -1));
}

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const runId = url.searchParams.get("run");

    if (runId) {
      const safe = runId.replace(/\.\./g, "");
      const summaryPath = path.join(root, "data", "output", "portfolio_backtests", safe, "summary.json");
      if (!fs.existsSync(summaryPath)) {
        return NextResponse.json({ error: "Run not found" }, { status: 404 });
      }
      const summary = JSON.parse(fs.readFileSync(summaryPath, "utf-8"));
      const monthlyPath = path.join(path.dirname(summaryPath), "monthly_returns.csv");
      let monthlyCsv = "";
      if (fs.existsSync(monthlyPath)) {
        monthlyCsv = fs.readFileSync(monthlyPath, "utf-8");
      }
      return NextResponse.json({ summary, monthlyCsv }, { headers: { "Cache-Control": "no-store" } });
    }

    const runs = listRuns(root);
    const allocDir = path.join(root, "data", "output", "portfolio_allocations");
    let latestAllocation: string | null = null;
    let latestAllocationDate: string | null = null;
    if (fs.existsSync(allocDir)) {
      const files = fs
        .readdirSync(allocDir)
        .filter((f) => f.startsWith("holdings_") && f.endsWith(".json"))
        .sort()
        .reverse();
      if (files.length) {
        latestAllocation = files[0];
        const m = files[0].match(/^holdings_(\d{4}-\d{2}-\d{2})\.json$/);
        latestAllocationDate = m?.[1] ?? null;
      }
    }

    return NextResponse.json(
      { runs, latestAllocation, latestAllocationDate },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    return NextResponse.json({ runs: [], error: String(e) }, { status: 500 });
  }
}
