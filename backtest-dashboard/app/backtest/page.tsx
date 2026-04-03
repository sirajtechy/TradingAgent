import BacktestRunner from "@/app/components/BacktestRunner";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Backtest Runner — Upload & Analyze",
  description:
    "Upload backtest JSON results, view aggregated metrics, confusion matrices, and export to Excel.",
};

export default function BacktestPage() {
  return <BacktestRunner />;
}
