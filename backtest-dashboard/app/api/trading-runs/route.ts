import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

function getMyTradingSpaceRoot(): string {
  return path.resolve(process.cwd(), "..");
}

function walkRunBundles(dir: string, acc: { relPath: string; mtimeMs: number; kind: string }[]): void {
  if (!fs.existsSync(dir)) return;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      walkRunBundles(p, acc);
    } else if (ent.name === "run_bundle.json") {
      const st = fs.statSync(p);
      const root = getMyTradingSpaceRoot();
      acc.push({
        relPath: path.relative(root, p),
        mtimeMs: st.mtimeMs,
        kind: "bundle",
      });
    } else if (ent.name === "master_pilot.json") {
      const st = fs.statSync(p);
      const root = getMyTradingSpaceRoot();
      acc.push({
        relPath: path.relative(root, p),
        mtimeMs: st.mtimeMs,
        kind: "master",
      });
    }
  }
}

export async function GET() {
  try {
    const root = getMyTradingSpaceRoot();
    const scanRoot = path.join(root, "data", "output", "trading_runs");
    const found: { relPath: string; mtimeMs: number; kind: string }[] = [];
    walkRunBundles(scanRoot, found);
    const runs = found
      .sort((a, b) => b.mtimeMs - a.mtimeMs)
      .map((f) => ({
        id: encodeURIComponent(f.relPath),
        relPath: f.relPath.replace(/\\/g, "/"),
        modified: new Date(f.mtimeMs).toISOString(),
        kind: f.kind,
      }));
    return NextResponse.json({ runs }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ runs: [] }, { status: 500 });
  }
}
