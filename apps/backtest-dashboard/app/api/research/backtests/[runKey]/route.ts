import { NextResponse } from "next/server";
import { NO_STORE, registryCli } from "@/app/lib/backtestRegistry";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ runKey: string }> };

export async function GET(_req: Request, { params }: Params) {
  try {
    const { runKey } = await params;
    const decoded = decodeURIComponent(runKey);
    const doc = await registryCli("get", [decoded]);
    if (!doc.ok) {
      return NextResponse.json(doc, { status: 404, headers: NO_STORE });
    }
    return NextResponse.json(doc, { headers: NO_STORE });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Run load failed" },
      { status: 500, headers: NO_STORE },
    );
  }
}
