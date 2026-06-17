import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function allocationDir(root: string): string {
  return path.join(root, "data", "output", "portfolio_allocations");
}

function parseDateFromFilename(filename: string): string | null {
  const m = filename.match(/^holdings_(\d{4}-\d{2}-\d{2})\.json$/);
  return m?.[1] ?? null;
}

function listHoldingsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.startsWith("holdings_") && f.endsWith(".json"))
    .sort()
    .reverse();
}

function resolveHoldingsPath(root: string, dateParam: string | null): { filePath: string; filename: string } | null {
  const dir = allocationDir(root);
  if (dateParam) {
    if (!DATE_RE.test(dateParam)) return null;
    const filename = `holdings_${dateParam}.json`;
    const filePath = path.join(dir, filename);
    if (!fs.existsSync(filePath)) return null;
    return { filePath, filename };
  }
  const files = listHoldingsFiles(dir);
  if (!files.length) return null;
  const filename = files[0];
  return { filePath: path.join(dir, filename), filename };
}

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const dateParam = url.searchParams.get("date");

    const resolved = resolveHoldingsPath(root, dateParam);
    if (!resolved) {
      const hint = dateParam
        ? `No holdings file for ${dateParam}. Expected holdings_${dateParam}.json`
        : "No allocation files yet. Run: ./bin/mts portfolio allocate --budget 200000";
      return NextResponse.json(
        { error: hint, expectedDir: "data/output/portfolio_allocations" },
        { status: 404, headers: { "Cache-Control": "no-store" } },
      );
    }

    const doc = JSON.parse(fs.readFileSync(resolved.filePath, "utf-8"));
    const asOf = parseDateFromFilename(resolved.filename) ?? doc.as_of ?? null;

    const holdings = Array.isArray(doc.holdings) ? doc.holdings : [];
    const enrichedHoldings = holdings.map((row: Record<string, unknown>) => {
      const ticker = String(row.ticker ?? "").toUpperCase();
      const breakdownRel = asOf
        ? path.join("data", "output", "research", asOf, `${ticker}_breakdown.md`)
        : null;
      const breakdownPath = breakdownRel ? path.join(root, breakdownRel) : null;
      return {
        ...row,
        breakdown_exists: breakdownPath ? fs.existsSync(breakdownPath) : false,
        breakdown_path: breakdownRel?.replace(/\\/g, "/") ?? null,
      };
    });

    return NextResponse.json(
      {
        ...doc,
        holdings: enrichedHoldings,
        source_file: resolved.filename,
        source_path: path.relative(root, resolved.filePath).replace(/\\/g, "/"),
        as_of: asOf ?? doc.as_of,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Failed to load allocation" },
      { status: 500 },
    );
  }
}
