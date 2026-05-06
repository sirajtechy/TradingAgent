import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const DATA_FILE = path.join(process.cwd(), "app", "data", "sectors-predictions.json");

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const raw = fs.readFileSync(DATA_FILE, "utf-8");
    const data = JSON.parse(raw);
    const stat = fs.statSync(DATA_FILE);
    return NextResponse.json(data, {
      headers: {
        "X-Last-Modified": stat.mtimeMs.toString(),
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "Data file not found" }, { status: 404 });
  }
}
