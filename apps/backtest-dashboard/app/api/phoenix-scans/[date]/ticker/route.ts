import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

function safeSectorDirname(sector: string): string {
  return sector
    .trim()
    .replaceAll("/", "_")
    .replaceAll("\\", "_")
    .replaceAll(" ", "_")
    .replaceAll("&", "and");
}

export async function GET(req: Request, ctx: { params: Promise<{ date: string }> }) {
  const { date } = await ctx.params;
  const { searchParams } = new URL(req.url);
  const ticker = (searchParams.get("ticker") || "").trim().toUpperCase();
  const sector = (searchParams.get("sector") || "").trim();

  if (!ticker || !sector) {
    return NextResponse.json({ error: "Missing ticker or sector" }, { status: 400 });
  }

  try {
    const sectorDir = safeSectorDirname(sector);
    const file = path.join(
      getMyTradingSpaceRoot(),
      "data",
      "output",
      "phoenix_sector_scans",
      date,
      sectorDir,
      `${ticker}.json`
    );

    if (!fs.existsSync(file)) {
      return NextResponse.json({ error: "Ticker report not found" }, { status: 404 });
    }
    const raw = fs.readFileSync(file, "utf-8");
    const parsed = JSON.parse(raw);
    return NextResponse.json(parsed, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Failed to read ticker report" }, { status: 500 });
  }
}

