import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

/** Only serve files under repo root / data / output */
function safeResolve(rel: string): string | null {
  const root = getMyTradingSpaceRoot();
  const normalized = path.normalize(rel).replace(/^(\.\.(\/|\\|$))+/, "");
  if (normalized.includes("..")) return null;
  if (!normalized.startsWith(`data${path.sep}output`)) return null;
  const full = path.join(root, normalized);
  if (!full.startsWith(root)) return null;
  return full;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const rel = searchParams.get("rel");
  if (!rel) {
    return NextResponse.json({ error: "Missing rel= path to run_bundle.json" }, { status: 400 });
  }
  const full = safeResolve(rel);
  if (!full || !fs.existsSync(full)) {
    return NextResponse.json({ error: "Not found or forbidden path" }, { status: 404 });
  }
  try {
    const raw = fs.readFileSync(full, "utf-8");
    const parsed = JSON.parse(raw);
    return NextResponse.json(parsed, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 500 });
  }
}
