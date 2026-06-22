import fs from "fs";
import path from "path";
import { getMyTradingSpaceRoot } from "@/app/lib/mtsRoot";

export type MasterPilotLocation = {
  path: string;
  rel: string;
  signalDate: string;
};

export function tradingRunsDir(root: string): string {
  return path.join(root, "data", "output", "trading_runs");
}

export function researchDir(root: string): string {
  return path.join(root, "data", "output", "research");
}

export function findMasterPilot(root: string, dateParam: string | null): MasterPilotLocation | null {
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
          /* skip corrupt */
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

export type MasterRow = {
  sector?: string;
  phoenix_signal?: string;
  phoenix_score?: number;
  fusion_final_signal?: string;
  fusion_orchestrator_score?: number;
  entry_price?: number | null;
  exit_price?: number | null;
  stop_price?: number | null;
  target_t1?: number | null;
  target_t2?: number | null;
  chase_risk?: string | null;
  extension_guardrail?: string | null;
  error?: string;
};

export function loadWatchlistRows(
  root: string,
  masterPath: string,
  asOf: string,
  options?: { tradeFocus?: boolean; signals?: Set<string> },
): Record<string, unknown>[] {
  const allowed = options?.signals ?? new Set(["BUY", "WATCH"]);
  const tradeFocus = options?.tradeFocus ?? false;
  const doc = JSON.parse(fs.readFileSync(masterPath, "utf-8")) as { tickers?: Record<string, MasterRow> };
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
    const breakdown = (analyzeDoc?.agent_breakdown || {}) as Record<string, unknown>;
    const agents = (breakdown.agents || {}) as Record<string, Record<string, unknown>>;
    const insider = agents.insider || {};

    tickers.push({
      ticker: tk.toUpperCase(),
      phoenix_signal: px,
      sector: row.sector || "Unknown",
      phoenix_score: score,
      fusion_final_signal: row.fusion_final_signal ?? null,
      fusion_orchestrator_score: row.fusion_orchestrator_score ?? null,
      entry_price: row.entry_price ?? null,
      stop_price: row.stop_price ?? null,
      target_t1: row.target_t1 ?? null,
      target_t2: row.target_t2 ?? null,
      chase_risk: row.chase_risk ?? null,
      extension_guardrail: row.extension_guardrail ?? null,
      analyze_cached: cached,
      analyze_path: cached ? path.relative(root, analyzePath).replace(/\\/g, "/") : null,
      advisory_verdict: fusion.advisory_verdict ?? null,
      orchestrator_score: fusion.orchestrator_score ?? null,
      insider_signal: insider.signal ?? null,
      insider_sell_value: (insider.metrics as Record<string, unknown> | undefined)?.sell_value ?? null,
    });
  }

  tickers.sort((a, b) => {
    const order = (s: unknown) => (s === "BUY" ? 0 : 1);
    const oa = order(a.phoenix_signal);
    const ob = order(b.phoenix_signal);
    if (oa !== ob) return oa - ob;
    return Number(b.phoenix_score ?? 0) - Number(a.phoenix_score ?? 0);
  });

  return tickers;
}
