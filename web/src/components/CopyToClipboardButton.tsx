"use client";

import { useState } from "react";

import { Button } from "@/components/Button";

export function CopyToClipboardButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // Ignore; user can still manually copy.
    }
  }

  return (
    <Button type="button" variant="secondary" className="h-10 px-4" onClick={onCopy}>
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

