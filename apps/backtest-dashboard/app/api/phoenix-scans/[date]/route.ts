import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

function getRunFile(date: string): string {
  return path.join(
    getMyTradingSpaceRoot(),
    "data",
    "output",
    "phoenix_sector_scans",
    date,
    `phoenix_sector_scan_${date}.json`
  );
}

function stripHeavyFields(result: any) {
  if (!result || typeof result !== "object") return result;
  // keep the page snappy; fetch full report per-ticker via the ticker endpoint
  const { report, ...rest } = result;
  return rest;
}

export async function GET(_: Request, ctx: { params: Promise<{ date: string }> }) {
  const { date } = await ctx.params;
  try {
    const file = getRunFile(date);
    if (!fs.existsSync(file)) {
      return NextResponse.json({ error: "Run not found" }, { status: 404 });
    }
    const raw = fs.readFileSync(file, "utf-8");
    const parsed = JSON.parse(raw);
    const meta = parsed?.meta ?? {};
    const results = Array.isArray(parsed?.results) ? parsed.results.map(stripHeavyFields) : [];
    const errors = Array.isArray(parsed?.errors) ? parsed.errors : [];

    return NextResponse.json(
      { meta, results, errors },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json({ error: "Failed to read run file" }, { status: 500 });
  }
}

