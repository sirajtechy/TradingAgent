import { NextResponse } from "next/server";
import { NO_STORE, registryCli } from "@/app/lib/backtestRegistry";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const period = url.searchParams.get("period") || "all";
    const limit = url.searchParams.get("limit") || "50";
    const doc = await registryCli("heatmap", ["--period", period, "--limit", limit]);
    return NextResponse.json(doc, { headers: NO_STORE });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Heatmap load failed" },
      { status: 500, headers: NO_STORE },
    );
  }
}
