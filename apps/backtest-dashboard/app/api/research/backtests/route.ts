import { NextResponse } from "next/server";
import { NO_STORE, registryCli } from "@/app/lib/backtestRegistry";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const sync = url.searchParams.get("sync") === "1";
    if (sync) {
      await registryCli("sync");
    }
    const limit = url.searchParams.get("limit") || "100";
    const doc = await registryCli("list", ["--limit", limit]);
    return NextResponse.json(doc, { headers: NO_STORE });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Backtest registry unavailable" },
      { status: 500, headers: NO_STORE },
    );
  }
}
