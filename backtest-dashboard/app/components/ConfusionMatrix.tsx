"use client";

import { ConfusionMatrix as CM } from "@/app/lib/types";

interface Props {
  cm: CM;
  title?: string;
}

export default function ConfusionMatrix({ cm, title }: Props) {
  const total = cm.buyUp + cm.buyDown + cm.sellUp + cm.sellDown + cm.holdUp + cm.holdDown;
  const maxVal = Math.max(cm.buyUp, cm.buyDown, cm.sellUp, cm.sellDown, cm.holdUp, cm.holdDown, 1);

  const cellColor = (val: number, isGood: boolean) => {
    const intensity = Math.round((val / maxVal) * 100);
    if (isGood) return `rgba(34, 197, 94, ${intensity / 100 * 0.5})`;
    return `rgba(239, 68, 68, ${intensity / 100 * 0.5})`;
  };

  const tp = cm.buyUp;
  const fp = cm.buyDown;
  const fn = cm.sellUp;
  const tn = cm.sellDown;
  const directional = tp + fp + fn + tn;
  const accuracy = directional ? ((tp + tn) / directional * 100).toFixed(1) : "N/A";
  const precision = (tp + fp) ? (tp / (tp + fp) * 100).toFixed(1) : "N/A";
  const recall = (tp + fn) ? (tp / (tp + fn) * 100).toFixed(1) : "N/A";
  const specificity = (tn + fp) ? (tn / (tn + fp) * 100).toFixed(1) : "N/A";

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
      {title && <h3 className="text-sm font-semibold text-gray-300 mb-4">{title}</h3>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left text-gray-500 font-medium py-2 px-3"></th>
              <th className="text-center text-gray-400 font-medium py-2 px-3">Actual UP</th>
              <th className="text-center text-gray-400 font-medium py-2 px-3">Actual DOWN</th>
              <th className="text-center text-gray-500 font-medium py-2 px-3">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-medium text-blue-400 py-2 px-3">Pred BUY</td>
              <td
                className="text-center py-2 px-3 rounded font-mono font-bold"
                style={{ backgroundColor: cellColor(cm.buyUp, true) }}
              >
                {cm.buyUp} <span className="text-xs text-gray-500">TP</span>
              </td>
              <td
                className="text-center py-2 px-3 rounded font-mono font-bold"
                style={{ backgroundColor: cellColor(cm.buyDown, false) }}
              >
                {cm.buyDown} <span className="text-xs text-gray-500">FP</span>
              </td>
              <td className="text-center py-2 px-3 text-gray-500 font-mono">{cm.buyUp + cm.buyDown}</td>
            </tr>
            <tr>
              <td className="font-medium text-red-400 py-2 px-3">Pred SELL</td>
              <td
                className="text-center py-2 px-3 rounded font-mono font-bold"
                style={{ backgroundColor: cellColor(cm.sellUp, false) }}
              >
                {cm.sellUp} <span className="text-xs text-gray-500">FN</span>
              </td>
              <td
                className="text-center py-2 px-3 rounded font-mono font-bold"
                style={{ backgroundColor: cellColor(cm.sellDown, true) }}
              >
                {cm.sellDown} <span className="text-xs text-gray-500">TN</span>
              </td>
              <td className="text-center py-2 px-3 text-gray-500 font-mono">{cm.sellUp + cm.sellDown}</td>
            </tr>
            <tr>
              <td className="font-medium text-gray-400 py-2 px-3">Pred HOLD</td>
              <td
                className="text-center py-2 px-3 rounded font-mono"
                style={{ backgroundColor: `rgba(156, 163, 175, ${(cm.holdUp / Math.max(maxVal, 1)) * 0.2})` }}
              >
                {cm.holdUp} <span className="text-xs text-gray-600">Miss</span>
              </td>
              <td
                className="text-center py-2 px-3 rounded font-mono"
                style={{ backgroundColor: `rgba(156, 163, 175, ${(cm.holdDown / Math.max(maxVal, 1)) * 0.2})` }}
              >
                {cm.holdDown} <span className="text-xs text-gray-600">Avoid</span>
              </td>
              <td className="text-center py-2 px-3 text-gray-500 font-mono">{cm.holdUp + cm.holdDown}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
        <div className="flex justify-between px-2 py-1 bg-gray-800/50 rounded">
          <span className="text-gray-500">Accuracy</span>
          <span className="font-mono text-gray-300">{accuracy}%</span>
        </div>
        <div className="flex justify-between px-2 py-1 bg-gray-800/50 rounded">
          <span className="text-gray-500">Precision</span>
          <span className="font-mono text-gray-300">{precision}%</span>
        </div>
        <div className="flex justify-between px-2 py-1 bg-gray-800/50 rounded">
          <span className="text-gray-500">Recall</span>
          <span className="font-mono text-gray-300">{recall}%</span>
        </div>
        <div className="flex justify-between px-2 py-1 bg-gray-800/50 rounded">
          <span className="text-gray-500">Specificity</span>
          <span className="font-mono text-gray-300">{specificity}%</span>
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-2 text-center">
        {total} total periods · {directional} directional · {total - directional} abstentions
      </p>
    </div>
  );
}
