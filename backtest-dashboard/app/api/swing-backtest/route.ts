import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// Reads the latest swing backtest JSON from the Python output directory.
// Absolute path so it works regardless of Next.js cwd.
const DATA_FILE = path.resolve(
  __dirname,
  "../../../../../../data/output/backtests/swing_2026/swing_backtest_latest.json"
);

// Fallback: if the above doesn't resolve in production, try relative to cwd
const FALLBACK = path.join(
  process.cwd(),
  "..",
  "data",
  "output",
  "backtests",
  "swing_2026",
  "swing_backtest_latest.json"
);

export const dynamic = "force-dynamic";

export async function GET() {
  const filePath = fs.existsSync(DATA_FILE) ? DATA_FILE : FALLBACK;

  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw);
    const stat = fs.statSync(filePath);

    return NextResponse.json(data, {
      headers: {
        "X-Last-Modified": stat.mtimeMs.toString(),
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Swing backtest data not found. Run the backtest script first." },
      { status: 404 }
    );
  }
}
