/**
 * Extension / chase display rules for Phoenix dashboard rows.
 * Uses signal-date lookback only (no forward Polygon data).
 */

export const WATCH_EXTENSION_MIN_SCORE = 60;

export type ExtensionRow = {
  phoenix_signal?: string | null;
  phoenix_score?: number | null;
  extension_justification?: string | null;
  extension_summary?: string | null;
  extension_daily_5d_pct?: number | null;
  extension_weekly_4w_pct?: number | null;
  chase_risk?: string | null;
};

/** BUY always; WATCH only when Phoenix score > 60 (closely watching). */
export function shouldShowExtensionJustification(row: ExtensionRow): boolean {
  const px = (row.phoenix_signal || "").toUpperCase();
  if (px === "BUY") return true;
  if (px === "WATCH") return (row.phoenix_score ?? 0) > WATCH_EXTENSION_MIN_SCORE;
  return false;
}

/** One-line "how much already up" text for the dashboard column. */
export function extensionJustificationText(row: ExtensionRow): string | null {
  if (row.extension_justification?.trim()) {
    return row.extension_justification.trim();
  }
  const parts: string[] = [];
  if (row.extension_daily_5d_pct != null && !Number.isNaN(Number(row.extension_daily_5d_pct))) {
    const n = Number(row.extension_daily_5d_pct);
    parts.push(`5d ${n >= 0 ? "+" : ""}${n.toFixed(1)}%`);
  }
  if (row.extension_weekly_4w_pct != null && !Number.isNaN(Number(row.extension_weekly_4w_pct))) {
    const n = Number(row.extension_weekly_4w_pct);
    parts.push(`4w ${n >= 0 ? "+" : ""}${n.toFixed(1)}%`);
  }
  if (parts.length) return parts.join(" · ");
  return null;
}

/** Trade-focus filter: all BUY + WATCH with score > 60. */
export function isTradeFocusRow(row: ExtensionRow): boolean {
  const px = (row.phoenix_signal || "").toUpperCase();
  if (px === "BUY") return true;
  if (px === "WATCH") return (row.phoenix_score ?? 0) > WATCH_EXTENSION_MIN_SCORE;
  return false;
}
