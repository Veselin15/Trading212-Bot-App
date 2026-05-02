"use client";

import { useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

export function DashboardUrlToasts() {
  const searchParams = useSearchParams();
  const lastHandled = useRef<string | null>(null);

  useEffect(() => {
    const checkout = searchParams.get("checkout");
    const license = searchParams.get("license");
    const sig = `${checkout ?? ""}|${license ?? ""}`;
    if (sig === "|" || lastHandled.current === sig) return;
    lastHandled.current = sig;

    if (checkout === "success") {
      toast.success("Subscription updated. It may take a few seconds for status to sync.");
    } else if (checkout === "cancel") {
      toast.message("Checkout canceled — no changes were made.");
    }

    if (license === "regenerated") {
      toast.success("License key regenerated.");
    }
  }, [searchParams]);

  return null;
}
