import { NextResponse } from "next/server";
import { NO_STORE, registryCli } from "@/app/lib/backtestRegistry";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const doc = await registryCli("timeline");
    return NextResponse.json(doc, { headers: NO_STORE });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Timeline load failed" },
      { status: 500, headers: NO_STORE },
    );
  }
}
