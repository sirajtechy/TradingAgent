"use client";

interface Props {
  data: { label: string; value: number; color: string }[];
  title: string;
}

export default function BarChart({ data, title }: Props) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">{title}</h3>
      <div className="space-y-2">
        {data.map((d) => (
          <div key={d.label} className="flex items-center gap-3">
            <span className="text-xs text-gray-400 w-28 shrink-0 truncate">{d.label.replace("_", " ")}</span>
            <div className="flex-1 h-6 bg-gray-800/50 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(d.value / maxVal) * 100}%`,
                  backgroundColor: d.color,
                }}
              />
            </div>
            <span className="text-xs font-mono text-gray-300 w-14 text-right">{d.value.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
