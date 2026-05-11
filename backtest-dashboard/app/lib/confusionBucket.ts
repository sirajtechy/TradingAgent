/**
 * Fusion directional vs labeled target-hit correctness (same rules as pilot confusion_matrix).
 */

export type ConfusionBucket = "TP" | "FP" | "TN" | "FN" | "NEUTRAL" | "UNLABELED";

export function confusionBucket(
  fusionFinalSignal: string | null | undefined,
  signalCorrect: boolean | null | undefined,
): ConfusionBucket {
  const sig = (fusionFinalSignal || "").toLowerCase();
  const sc = signalCorrect;
  if (sc === null || sc === undefined) {
    return sig === "bullish" || sig === "bearish" ? "UNLABELED" : "NEUTRAL";
  }
  if (sig === "bullish") return sc ? "TP" : "FP";
  if (sig === "bearish") return sc ? "TN" : "FN";
  return "NEUTRAL";
}

export function confusionCells(bucket: ConfusionBucket): { TP: string; FP: string; TN: string; FN: string } {
  return {
    TP: bucket === "TP" ? "✓" : "",
    FP: bucket === "FP" ? "✓" : "",
    TN: bucket === "TN" ? "✓" : "",
    FN: bucket === "FN" ? "✓" : "",
  };
}
