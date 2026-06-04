import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { compareRunBundles, type RunBundle } from "../../../lib/compareRunBundles";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";

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
  const a = searchParams.get("a");
  const b = searchParams.get("b");
  if (!a || !b) {
    return NextResponse.json({ error: "Need query params a= and b= (relative paths to run_bundle.json)" }, { status: 400 });
  }
  const pa = safeResolve(a);
  const pb = safeResolve(b);
  if (!pa || !pb || !fs.existsSync(pa) || !fs.existsSync(pb)) {
    return NextResponse.json({ error: "Bundle not found" }, { status: 404 });
  }
  try {
    const ba = JSON.parse(fs.readFileSync(pa, "utf-8")) as RunBundle;
    const bb = JSON.parse(fs.readFileSync(pb, "utf-8")) as RunBundle;
    const cmp = compareRunBundles(ba, bb);
    return NextResponse.json(
      {
        ...cmp,
        meta: {
          compared_at: new Date().toISOString(),
          path_a: a,
          path_b: b,
        },
      },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json({ error: "Compare failed" }, { status: 500 });
  }
}
