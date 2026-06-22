import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";
import {
  artifactPathFromRunKey,
  findLatestMasterPilot,
  findLatestVerifyReport,
  loadVerifyIndex,
  loadVerifyReport,
  listVerifyReports,
  rebuildVerifyIndex,
  runVerifyBatchCli,
  runVerifyCli,
  verifyReportPathForArtifact,
} from "@/app/lib/backtestVerify";
import { NO_STORE } from "@/app/lib/backtestRegistry";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function GET(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const url = new URL(req.url);
    const runKey = url.searchParams.get("run");
    const rel = url.searchParams.get("rel");
    const signalDate = url.searchParams.get("signal_date");
    const latest = url.searchParams.get("latest") === "1";
    const indexOnly = url.searchParams.get("index") === "1";

    if (indexOnly) {
      let index = loadVerifyIndex(root);
      if (!index?.runs?.length) {
        index = await rebuildVerifyIndex(root);
      }
      return NextResponse.json({ ok: true, index }, { headers: NO_STORE });
    }

    let reportPath: string | null = null;
    let artifactPath: string | null = null;
    let artifactRel: string | null = null;

    if (runKey) {
      artifactPath = artifactPathFromRunKey(root, runKey);
      if (artifactPath) {
        artifactRel = path
          .relative(path.join(root, "data", "output", "trading_runs"), artifactPath)
          .replace(/\\/g, "/");
        reportPath = verifyReportPathForArtifact(root, artifactPath);
      }
    } else if (rel) {
      artifactRel = rel.replace(/^\/+/, "");
      artifactPath = path.join(root, "data", "output", "trading_runs", artifactRel);
      if (!artifactPath.endsWith(".json")) {
        artifactPath = path.join(path.dirname(artifactPath), "master_pilot.json");
      }
      reportPath = verifyReportPathForArtifact(root, artifactPath);
    } else if (signalDate) {
      artifactRel = `sector_information-technology_${signalDate}/master_pilot.json`;
      artifactPath = path.join(root, "data", "output", "trading_runs", artifactRel);
      reportPath = verifyReportPathForArtifact(root, artifactPath);
    } else if (latest) {
      const art = findLatestMasterPilot(root);
      if (art) {
        artifactPath = art.path;
        artifactRel = art.rel;
        reportPath = verifyReportPathForArtifact(root, artifactPath);
      }
    }

    const reports = listVerifyReports(root).map((r) => ({
      rel: r.rel,
      modified: new Date(r.mtime).toISOString(),
    }));

    const doc = reportPath ? loadVerifyReport(reportPath) : null;
    const latestReport = findLatestVerifyReport(root);
    const index = loadVerifyIndex(root) ?? (await rebuildVerifyIndex(root));

    return NextResponse.json(
      {
        ok: true,
        artifact: artifactPath
          ? {
              path: artifactPath,
              rel: artifactRel,
              exists: fs.existsSync(artifactPath),
            }
          : null,
        report: doc
          ? {
              path: reportPath,
              rel: reportPath ? path.relative(root, reportPath).replace(/\\/g, "/") : null,
              exists: true,
              summary: doc.summary,
              verified_summary: doc.verified_summary,
              meta: doc.meta,
            }
          : reportPath
            ? {
                path: reportPath,
                rel: path.relative(root, reportPath).replace(/\\/g, "/"),
                exists: false,
              }
            : null,
        latest_report: latestReport,
        reports,
        index,
      },
      { headers: NO_STORE },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Verify load failed" },
      { status: 500, headers: NO_STORE },
    );
  }
}

export async function POST(req: Request) {
  try {
    const root = getMyTradingSpaceRoot();
    const body = (await req.json().catch(() => ({}))) as {
      run?: string;
      rel?: string;
      rateLimit?: number;
      sample?: number;
      batch?: boolean;
      glob?: string;
      force?: boolean;
    };

    if (body.batch) {
      const result = await runVerifyBatchCli(root, {
        glob: body.glob ?? "sector_information-technology_*",
        rateLimit: body.rateLimit ?? 2,
        force: body.force,
      });
      const index = loadVerifyIndex(root) ?? (await rebuildVerifyIndex(root));
      return NextResponse.json(
        {
          ok: true,
          batch: true,
          index,
          stdout_tail: result.stdout.slice(-3000),
          stderr_tail: result.stderr.slice(-1000) || undefined,
        },
        { headers: NO_STORE },
      );
    }

    let artifactPath: string | null = null;
    if (body.run) {
      artifactPath = artifactPathFromRunKey(root, body.run);
    } else if (body.rel) {
      const rel = body.rel.replace(/^\/+/, "");
      artifactPath = path.join(root, "data", "output", "trading_runs", rel);
      if (!artifactPath.endsWith(".json")) {
        artifactPath = path.join(path.dirname(artifactPath), "master_pilot.json");
      }
    } else {
      artifactPath = findLatestMasterPilot(root)?.path ?? null;
    }

    if (!artifactPath || !fs.existsSync(artifactPath)) {
      return NextResponse.json(
        { ok: false, error: "Artifact not found. Pass run, rel, or ensure a master_pilot.json exists." },
        { status: 404, headers: NO_STORE },
      );
    }

    const result = await runVerifyCli(root, artifactPath, {
      rateLimit: body.rateLimit ?? 2,
      sample: body.sample,
    });
    const doc = loadVerifyReport(result.reportPath);
    const index = await rebuildVerifyIndex(root);

    return NextResponse.json(
      {
        ok: result.exitCode !== 1,
        exit_code: result.exitCode,
        report_path: result.reportPath,
        report_rel: path.relative(root, result.reportPath).replace(/\\/g, "/"),
        summary: doc?.summary,
        verified_summary: doc?.verified_summary,
        index,
        stderr: result.stderr?.slice(-2000) || undefined,
      },
      { status: result.exitCode === 1 ? 500 : 200, headers: NO_STORE },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "Verify run failed" },
      { status: 500, headers: NO_STORE },
    );
  }
}
