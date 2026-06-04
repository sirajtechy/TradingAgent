"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TradingRunsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/research/runs");
  }, [router]);
  return (
    <div className="min-h-screen flex items-center justify-center text-[var(--text-dim)]">
      Redirecting to /research/runs…
    </div>
  );
}
