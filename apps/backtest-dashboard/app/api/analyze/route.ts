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
const FUSION_MODES = new Set(["phoenix-fa", "phoenix", "fundamental", "full"]);

function researchDir(root: string): string {
  return path.join(root, "data", "output", "research");
}

function analyzeJsonFilename(ticker: string): string {
  return `${ticker.trim().toUpperCase()}_analyze.json`;
}

function breakdownFilename(ticker: string): string {
  return `${ticker.trim().toUpperCase()}_breakdown.md`;
}

function defaultYesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function listResearchDates(root: string): string[] {
  const dir = researchDir(root);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && DATE_RE.test(e.name))
    .map((e) => e.name)
    .sort()
    .reverse();
}

function findLatestAnalyzeDate(root: string, ticker: string): string | null {
  const filename = analyzeJsonFilename(ticker);
  for (const date of listResearchDates(root)) {
    const filePath = path.join(researchDir(root), date, filename);
    if (fs.existsSync(filePath)) return date;
  }
  return null;
}

function resolveAnalyzePath(
  root: string,
  ticker: string,
  dateParam: string | null,
): { filePath: string; date: string; filename: string } | null {
  const tk = ticker.trim().toUpperCase();
  const filename = analyzeJsonFilename(tk);

  if (dateParam) {
    if (!DATE_RE.test(dateParam)) return null;
    const filePath = path.join(researchDir(root), dateParam, filename);
    if (!fs.existsSync(filePath)) return null;
    return { filePath, date: dateParam, filename };
  }

  const latest = findLatestAnalyzeDate(root, tk);
  if (!latest) return null;
  const filePath = path.join(researchDir(root), latest, filename);
  return { filePath, date: latest, filename };
}

function resolvePython(root: string): string {
  const venv = path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  return "python3";
}

async function runAnalyzePipeline(
  root: string,
  ticker: string,
  date: string,
  fusion: string,
  refreshContext = false,
): Promise<Record<string, unknown>> {
  const py = resolvePython(root);
  const args = ["-m", "pipelines", "analyze", "--ticker", ticker, "--date", date, "--fusion", fusion];
  if (refreshContext) args.push("--refresh-context");
  const { stdout, stderr } = await execFileAsync(py, args, {
    cwd: root,
    timeout: 280_000,
    maxBuffer: 32 * 1024 * 1024,
    env: { ...process.env, PYTHONPATH: root },
  });
  if (stderr?.trim()) {
    console.warn("[analyze API] stderr:", stderr.slice(0, 500));
  }
  return JSON.parse(stdout) as Record<string, unknown>;
}

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const tickerParam = url.searchParams.get("ticker");
    if (!tickerParam?.trim()) {
      return NextResponse.json({ error: "ticker is required" }, { status: 400 });
    }

    const ticker = tickerParam.trim().toUpperCase();
    const fusion = (url.searchParams.get("fusion") ?? "full").toLowerCase();
    if (!FUSION_MODES.has(fusion)) {
      return NextResponse.json({ error: `Invalid fusion: ${fusion}` }, { status: 400 });
    }

    const source = (url.searchParams.get("source") ?? "file").toLowerCase();
    const dateParam = url.searchParams.get("date");
    if (dateParam && !DATE_RE.test(dateParam)) {
      return NextResponse.json({ error: `Invalid date: ${dateParam}` }, { status: 400 });
    }

    const resolvedDate = dateParam ?? findLatestAnalyzeDate(root, ticker) ?? defaultYesterday();
    const breakdownRel = path.join("data", "output", "research", resolvedDate, breakdownFilename(ticker));
    const breakdownPath = path.join(root, breakdownRel);

    if (source === "file") {
      const resolved = resolveAnalyzePath(root, ticker, dateParam);
      if (resolved) {
        const doc = JSON.parse(fs.readFileSync(resolved.filePath, "utf-8"));
        return NextResponse.json(
          {
            ok: true,
            doc,
            ticker,
            as_of_date: doc.as_of_date ?? resolved.date,
            fusion_mode: doc.fusion_mode ?? fusion,
            source: "file",
            cached: true,
            source_file: resolved.filename,
            source_path: path.relative(root, resolved.filePath).replace(/\\/g, "/"),
            breakdown_exists: fs.existsSync(breakdownPath),
            breakdown_path: breakdownRel.replace(/\\/g, "/"),
          },
          { headers: { "Cache-Control": "no-store" } },
        );
      }
    }

    const doc = await runAnalyzePipeline(
      root,
      ticker,
      resolvedDate,
      fusion,
      url.searchParams.get("refresh_context") === "1",
    );
    const analyzeJsonPath = typeof doc.analyze_json_path === "string" ? doc.analyze_json_path : null;

    return NextResponse.json(
      {
        ok: doc.ok !== false,
        doc,
        ticker,
        as_of_date: (doc.as_of_date as string) ?? resolvedDate,
        fusion_mode: (doc.fusion_mode as string) ?? fusion,
        source: "run",
        cached: false,
        source_file: analyzeJsonPath ? path.basename(analyzeJsonPath) : null,
        source_path: analyzeJsonPath,
        breakdown_exists: fs.existsSync(breakdownPath),
        breakdown_path: breakdownRel.replace(/\\/g, "/"),
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to load analyze";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
