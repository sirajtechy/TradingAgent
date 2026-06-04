import fs from "fs";
import path from "path";

/** Repo root (MyTradingSpace/) — works from apps/backtest-dashboard or symlink. */
export function getMyTradingSpaceRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    if (
      fs.existsSync(path.join(dir, "bin", "mts")) ||
      fs.existsSync(path.join(dir, "pipelines", "analyze.py"))
    ) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return path.resolve(process.cwd(), "..", "..");
}
