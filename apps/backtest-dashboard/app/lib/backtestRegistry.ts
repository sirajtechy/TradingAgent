import { execFile } from "child_process";
import fs from "fs";
import path from "path";
import { promisify } from "util";
import { getMyTradingSpaceRoot } from "./mtsRoot";

const execFileAsync = promisify(execFile);

function pythonBin(root: string): string {
  const venv = path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  return "python3";
}

export async function registryCli(
  subcommand: string,
  extraArgs: string[] = [],
): Promise<Record<string, unknown>> {
  const root = getMyTradingSpaceRoot();
  const py = pythonBin(root);
  const script = path.join(root, "core", "persistence", "registry_cli.py");
  const { stdout } = await execFileAsync(py, [script, subcommand, ...extraArgs], {
    cwd: root,
    env: { ...process.env, PYTHONPATH: root },
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(stdout) as Record<string, unknown>;
}

export const NO_STORE = { "Cache-Control": "no-store, max-age=0" };
