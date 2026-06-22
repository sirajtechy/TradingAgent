import { execFile } from "child_process";
import fs from "fs";
import path from "path";
import { promisify } from "util";
import { getMyTradingSpaceRoot } from "./mtsRoot";

const execFileAsync = promisify(execFile);

export type VerifyReportDoc = {
  meta?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  verified_summary?: VerifiedSummaryDoc;
  rows?: unknown[];
};

export type VerifiedSummaryDoc = {
  agent?: string;
  description?: string;
  artifact_claimed?: {
    bullish_tp?: number;
    bullish_fp?: number;
    bullish_total?: number;
  };
  polygon_verified?: {
    confirmed_tp?: number;
    disputed_tp?: number;
    confirmed_fp?: number;
    disputed_fp?: number;
    skipped_bullish?: number;
    tp_confirmation_rate_pct?: number | null;
    price_rows_pass?: number;
    price_rows_fail?: number;
    price_rows_skip?: number;
  };
  verified_tp_tickers?: VerifiedTickerRow[];
  disputed_tp_tickers?: VerifiedTickerRow[];
  verified_fp_tickers?: VerifiedTickerRow[];
  disputed_fp_tickers?: VerifiedTickerRow[];
  skipped_bullish_tickers?: VerifiedTickerRow[];
};

export type VerifiedTickerRow = {
  ticker: string;
  signal_date?: string;
  result_date?: string;
  entry_price?: number | null;
  target_price?: number | null;
  target_hit_date?: string | null;
  artifact_target_hit?: boolean | null;
  recomputed_target_hit?: boolean | null;
  polygon_confirmed?: boolean;
  mismatches?: { field: string; expected: unknown; actual: unknown }[];
  detail?: string | null;
};

function pythonBin(root: string): string {
  const venv = path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  const parentVenv = path.join(root, "..", ".venv", "bin", "python");
  if (fs.existsSync(parentVenv)) return parentVenv;
  return "python3";
}

export function verifyOutputDir(root: string): string {
  return path.join(root, "data", "output", "verify");
}

export function verifyIndexPath(root: string): string {
  return path.join(verifyOutputDir(root), "verify_index.json");
}

export type VerifyIndexRun = {
  signal_date?: string;
  folder?: string;
  artifact_rel?: string;
  report_rel?: string | null;
  verified?: boolean;
  verified_at?: string;
  ticker_count?: number;
  rows_total?: number;
  rows_pass?: number;
  rows_fail?: number;
  rows_skip?: number;
  pass_rate_pct?: number;
  artifact_tp?: number;
  artifact_fp?: number;
  confirmed_tp?: number;
  disputed_tp?: number;
  confirmed_fp?: number;
  disputed_fp?: number;
  tp_confirmation_rate_pct?: number | null;
};

export type VerifyIndexDoc = {
  updated_at?: string;
  runs?: VerifyIndexRun[];
  aggregate?: {
    total_artifacts?: number;
    verified_count?: number;
    missing_count?: number;
    total_artifact_tp?: number;
    total_confirmed_tp?: number;
    total_disputed_tp?: number;
    total_rows_pass?: number;
    total_rows_fail?: number;
    overall_tp_confirmation_rate_pct?: number | null;
  };
};

export function loadVerifyIndex(root: string): VerifyIndexDoc | null {
  const p = verifyIndexPath(root);
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8")) as VerifyIndexDoc;
  } catch {
    return null;
  }
}

export async function rebuildVerifyIndex(root: string, glob = "sector_information-technology_*"): Promise<VerifyIndexDoc> {
  const py = pythonBin(root);
  const script = path.join(root, "scripts", "verify", "verify_batch.py");
  await execFileAsync(py, [script, "--glob", glob, "--index-only"], {
    cwd: root,
    env: { ...process.env, PYTHONPATH: root },
    maxBuffer: 8 * 1024 * 1024,
  });
  return loadVerifyIndex(root) ?? { runs: [], aggregate: {} };
}

export async function runVerifyBatchCli(
  root: string,
  options?: { glob?: string; rateLimit?: number; force?: boolean },
): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  const py = pythonBin(root);
  const script = path.join(root, "scripts", "verify", "verify_batch.py");
  const args = [script, "--glob", options?.glob ?? "sector_information-technology_*", "--rate-limit", String(options?.rateLimit ?? 2)];
  if (options?.force) args.push("--force");
  const { stdout, stderr } = await execFileAsync(py, args, {
    cwd: root,
    env: { ...process.env, PYTHONPATH: root, POLYGON_REQUESTS_PER_SECOND: String(options?.rateLimit ?? 2) },
    maxBuffer: 64 * 1024 * 1024,
    timeout: 60 * 60 * 1000,
  });
  return { exitCode: 0, stdout, stderr };
}

export function artifactRelFromSignalDate(root: string, signalDate: string, globPrefix = "sector_information-technology"): string | null {
  const folder = `${globPrefix}_${signalDate}`;
  const full = path.join(root, "data", "output", "trading_runs", folder, "master_pilot.json");
  return fs.existsSync(full) ? `${folder}/master_pilot.json` : null;
}

/** Map master_pilot path → default verify report filename stem. */
export function verifyReportPathForArtifact(root: string, artifactPath: string): string {
  const parent = path.basename(path.dirname(artifactPath));
  return path.join(verifyOutputDir(root), `${parent}_verify_report.json`);
}

export function listVerifyReports(root: string): { path: string; rel: string; mtime: number }[] {
  const dir = verifyOutputDir(root);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith("_verify_report.json"))
    .map((f) => {
      const full = path.join(dir, f);
      return { path: full, rel: path.join("data", "output", "verify", f), mtime: fs.statSync(full).mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
}

export function loadVerifyReport(reportPath: string): VerifyReportDoc | null {
  if (!fs.existsSync(reportPath)) return null;
  try {
    const doc = JSON.parse(fs.readFileSync(reportPath, "utf-8")) as VerifyReportDoc;
    if (!doc.verified_summary && doc.meta?.verified_summary) {
      doc.verified_summary = doc.meta.verified_summary as VerifiedSummaryDoc;
    }
    return doc;
  } catch {
    return null;
  }
}

export function artifactPathFromRunKey(root: string, runKey: string): string | null {
  const full = path.join(root, "data", "output", "trading_runs", runKey.replace(/^\/+/, ""));
  if (fs.existsSync(full)) return full;
  const asMaster = full.endsWith("master_pilot.json") ? full : path.join(full, "master_pilot.json");
  return fs.existsSync(asMaster) ? asMaster : null;
}

export async function runVerifyCli(
  root: string,
  artifactPath: string,
  options?: { rateLimit?: number; sample?: number },
): Promise<{ exitCode: number; reportPath: string; stdout: string; stderr: string }> {
  const py = pythonBin(root);
  const script = path.join(root, "scripts", "verify", "verify_backtest.py");
  const args = [
    script,
    "--input",
    artifactPath,
    "--rate-limit",
    String(options?.rateLimit ?? 2),
    "--quiet",
  ];
  if (options?.sample) {
    args.push("--sample", String(options.sample));
  }
  const reportPath = verifyReportPathForArtifact(root, artifactPath);
  args.push("--output", reportPath);

  const { stdout, stderr } = await execFileAsync(py, args, {
    cwd: root,
    env: { ...process.env, PYTHONPATH: root, POLYGON_REQUESTS_PER_SECOND: String(options?.rateLimit ?? 2) },
    maxBuffer: 32 * 1024 * 1024,
    timeout: 15 * 60 * 1000,
  });

  let exitCode = 0;
  if (!fs.existsSync(reportPath)) {
    exitCode = 1;
  } else {
    const doc = loadVerifyReport(reportPath);
    const fails = (doc?.summary?.rows_fail as number | undefined) ?? 0;
    if (fails > 0) exitCode = 2;
  }

  return { exitCode, reportPath, stdout, stderr };
}

export function findLatestVerifyReport(root: string): { path: string; rel: string } | null {
  const listed = listVerifyReports(root);
  if (!listed.length) return null;
  const best = listed[0];
  return { path: best.path, rel: best.rel };
}

export function findLatestMasterPilot(root: string): { path: string; rel: string } | null {
  const runs = path.join(root, "data", "output", "trading_runs");
  if (!fs.existsSync(runs)) return null;
  let best: { path: string; rel: string; mtime: number } | null = null;
  function walk(dir: string, prefix: string) {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, ent.name);
      const rel = prefix ? `${prefix}/${ent.name}` : ent.name;
      if (ent.isDirectory()) walk(full, rel);
      else if (ent.name === "master_pilot.json") {
        const mtime = fs.statSync(full).mtimeMs;
        if (!best || mtime > best.mtime) best = { path: full, rel, mtime };
      }
    }
  }
  walk(runs, "");
  if (!best) return null;
  return { path: best.path, rel: best.rel };
}
