import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { execFile } from "child_process";
import { promisify } from "util";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const execFileAsync = promisify(execFile);
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

type MasterRow = {
  phoenix_signal?: string;
  phoenix_score?: number;
  sector?: string;
  error?: string;
  fusion?: { final_signal?: string; orchestrator_score?: number };
};

function tradingRunsDir(root: string): string {
  return path.join(root, "data", "output", "trading_runs");
}

function researchDir(root: string): string {
  return path.join(root, "data", "output", "research");
}

function resolvePython(root: string): string {
  const venv = path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  return "python3";
}

function findMasterPilot(root: string, dateParam: string | null): { path: string; rel: string; signalDate: string } | null {
  const runs = tradingRunsDir(root);
  if (!fs.existsSync(runs)) return null;

  if (dateParam) {
    const unified = path.join(runs, `unified_master_${dateParam}`, "master_pilot.json");
    if (fs.existsSync(unified)) {
      return { path: unified, rel: `unified_master_${dateParam}/master_pilot.json`, signalDate: dateParam };
    }
  }

  const candidates: { path: string; rel: string; mtime: number; signalDate: string }[] = [];

  function walk(dir: string, prefix: string) {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, ent.name);
      const rel = prefix ? `${prefix}/${ent.name}` : ent.name;
      if (ent.isDirectory()) walk(full, rel);
      else if (ent.name === "master_pilot.json") {
        try {
          const doc = JSON.parse(fs.readFileSync(full, "utf-8"));
          const sig = String((doc.manifest || {}).signal_date || "").slice(0, 10);
          if (sig) {
            candidates.push({ path: full, rel, mtime: fs.statSync(full).mtimeMs, signalDate: sig });
          }
        } catch {
          /* skip */
        }
      }
    }
  }
  walk(runs, "");

  candidates.sort((a, b) => {
    const aU = a.rel.includes("unified_master_") ? 1 : 0;
    const bU = b.rel.includes("unified_master_") ? 1 : 0;
    if (aU !== bU) return bU - aU;
    return b.mtime - a.mtime;
  });

  const best = candidates[0];
  if (!best) return null;
  if (dateParam && best.signalDate !== dateParam) {
    const match = candidates.find((c) => c.signalDate === dateParam);
    if (match) return { path: match.path, rel: match.rel, signalDate: match.signalDate };
  }
  return { path: best.path, rel: best.rel, signalDate: best.signalDate };
}

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const dateParam = url.searchParams.get("date");
    const tradeFocus = url.searchParams.get("trade_focus") === "1";
    const allowed = new Set(
      (url.searchParams.get("signals") ?? "BUY,WATCH")
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean),
    );

    const master = findMasterPilot(root, dateParam);
    if (!master) {
      return NextResponse.json(
        {
          ok: false,
          error: "No master_pilot.json found. Run ./bin/mts daily or ./bin/mts unified first.",
        },
        { status: 404 },
      );
    }

    const doc = JSON.parse(fs.readFileSync(master.path, "utf-8")) as {
      tickers?: Record<string, MasterRow>;
    };
    const asOf = master.signalDate;
    const tickers: Record<string, unknown>[] = [];

    for (const [tk, row] of Object.entries(doc.tickers || {})) {
      if (!row || row.error) continue;
      const px = String(row.phoenix_signal || "").toUpperCase();
      if (!allowed.has(px)) continue;
      const score = row.phoenix_score ?? null;
      if (tradeFocus && px === "WATCH" && (score === null || score <= 60)) continue;

      const analyzePath = path.join(researchDir(root), asOf, `${tk.toUpperCase()}_analyze.json`);
      const cached = fs.existsSync(analyzePath);
      let analyzeDoc: Record<string, unknown> | null = null;
      if (cached) {
        try {
          analyzeDoc = JSON.parse(fs.readFileSync(analyzePath, "utf-8"));
        } catch {
          analyzeDoc = null;
        }
      }
      const fusion = (analyzeDoc?.fusion || {}) as Record<string, unknown>;
      const agents = ((analyzeDoc?.agent_breakdown as Record<string, unknown>)?.agents || {}) as Record<
        string,
        Record<string, unknown>
      >;
      const newsAgent = agents.news || {};

      tickers.push({
        ticker: tk.toUpperCase(),
        phoenix_signal: px,
        sector: row.sector || "Unknown",
        phoenix_score: score,
        fusion_final_signal: row.fusion?.final_signal ?? null,
        fusion_orchestrator_score: row.fusion?.orchestrator_score ?? null,
        analyze_cached: cached,
        analyze_path: cached ? path.relative(root, analyzePath).replace(/\\/g, "/") : null,
        advisory_verdict: fusion.advisory_verdict ?? null,
        orchestrator_score: fusion.orchestrator_score ?? null,
        news_one_liner: newsAgent.one_liner ?? null,
        news_headline_count: Array.isArray(newsAgent.headlines) ? newsAgent.headlines.length : 0,
      });
    }

    tickers.sort((a, b) => {
      const order = (s: unknown) => (s === "BUY" ? 0 : 1);
      const oa = order(a.phoenix_signal);
      const ob = order(b.phoenix_signal);
      if (oa !== ob) return oa - ob;
      return Number(b.phoenix_score ?? 0) - Number(a.phoenix_score ?? 0);
    });

    return NextResponse.json(
      {
        ok: true,
        as_of_date: asOf,
        meta: {
          signal_date: asOf,
          source_path: path.relative(root, master.path).replace(/\\/g, "/"),
          source_rel: master.rel,
          buy_count: tickers.filter((t) => t.phoenix_signal === "BUY").length,
          watch_count: tickers.filter((t) => t.phoenix_signal === "WATCH").length,
          total: tickers.length,
          analyzed_count: tickers.filter((t) => t.analyze_cached).length,
        },
        tickers,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Failed to load watchlist" },
      { status: 500 },
    );
  }
}

export async function POST(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
    const dateParam = typeof body.date === "string" ? body.date : null;
    if (dateParam && !DATE_RE.test(dateParam)) {
      return NextResponse.json({ error: "Invalid date" }, { status: 400 });
    }

    const py = resolvePython(root);
    const args = [
      "-m",
      "pipelines",
      "analyze",
      "--watchlist",
      "--fusion",
      "full",
      "--export-breakdown",
      "--refresh-context",
    ];
    if (dateParam) args.push("--date", dateParam);
    if (body.trade_focus) args.push("--trade-focus");
    if (body.force) args.push("--force");
    if (typeof body.max_tickers === "number") {
      args.push("--max-tickers", String(body.max_tickers));
    }

    const { stdout } = await execFileAsync(py, args, {
      cwd: root,
      timeout: 280_000,
      maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, PYTHONPATH: root },
    });

    const doc = JSON.parse(stdout) as Record<string, unknown>;
    return NextResponse.json({ ok: true, doc }, { headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Watchlist batch failed" },
      { status: 500 },
    );
  }
}
