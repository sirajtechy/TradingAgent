"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PhoenixWatchBuyRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/research/phoenix");
  }, [router]);
  return (
    <div className="min-h-screen flex items-center justify-center text-[var(--text-dim)]">
      Redirecting to /research/phoenix…
    </div>
  );
}
