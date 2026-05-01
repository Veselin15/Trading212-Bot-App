"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="top-right"
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "border border-white/10 bg-slate-950/95 text-slate-50 shadow-[0_10px_30px_-18px_rgba(0,0,0,0.8)]",
          description: "text-slate-300",
          actionButton: "bg-sky-500 text-slate-950 hover:bg-sky-400",
          cancelButton: "bg-white/5 text-slate-50 hover:bg-white/10",
        },
      }}
    />
  );
}

