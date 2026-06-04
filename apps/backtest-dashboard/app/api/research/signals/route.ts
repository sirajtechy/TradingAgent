import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

const DEFAULT_REL = path.join(
  "data",
  "output",
  "trading_runs",
  "phoenix_signals_reconciled.json",
);

export async function GET() {
  try {
    const root = getMyTradingSpaceRoot();
    const jsonPath = path.join(root, DEFAULT_REL);
    const xlsxPath = jsonPath.replace(/\.json$/i, ".xlsx");

    if (!fs.existsSync(jsonPath)) {
      return NextResponse.json(
        {
          ok: false,
          error: "No reconciled signals file. Run: ./bin/mts export --from YYYY-MM-DD --to YYYY-MM-DD",
          expectedPath: DEFAULT_REL.replace(/\\/g, "/"),
        },
        { status: 404, headers: { "Cache-Control": "no-store" } },
      );
    }

    const doc = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
    return NextResponse.json(
      {
        ok: true,
        jsonPath: DEFAULT_REL.replace(/\\/g, "/"),
        xlsxPath: DEFAULT_REL.replace(/\.json$/i, ".xlsx").replace(/\\/g, "/"),
        xlsxExists: fs.existsSync(xlsxPath),
        ...doc,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Failed to load signals" },
      { status: 500 },
    );
  }
}
