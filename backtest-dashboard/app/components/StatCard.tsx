"use client";

interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  color?: "blue" | "emerald" | "purple" | "amber" | "red" | "gray";
  large?: boolean;
}

const colorMap = {
  blue: "from-blue-500/20 to-blue-600/5 border-blue-500/30",
  emerald: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/30",
  purple: "from-purple-500/20 to-purple-600/5 border-purple-500/30",
  amber: "from-amber-500/20 to-amber-600/5 border-amber-500/30",
  red: "from-red-500/20 to-red-600/5 border-red-500/30",
  gray: "from-gray-500/20 to-gray-600/5 border-gray-500/30",
};

const textMap = {
  blue: "text-blue-400",
  emerald: "text-emerald-400",
  purple: "text-purple-400",
  amber: "text-amber-400",
  red: "text-red-400",
  gray: "text-gray-400",
};

export default function StatCard({ label, value, subtitle, color = "gray", large }: StatCardProps) {
  return (
    <div
      className={`bg-gradient-to-br ${colorMap[color]} border rounded-xl p-4 ${
        large ? "col-span-2" : ""
      }`}
    >
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">{label}</p>
      <p className={`${large ? "text-3xl" : "text-2xl"} font-bold mt-1 ${textMap[color]}`}>
        {value}
      </p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}
