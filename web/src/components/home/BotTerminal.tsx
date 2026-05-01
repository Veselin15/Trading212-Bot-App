"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

const LINES = [
  "> System initialized...",
  "> Connecting to Trading212 API... [OK]",
  "> Scanning EU markets...",
  "> Awaiting live signals...",
] as const;

export function BotTerminal() {
  const reduce = useReducedMotion();
  const [lineIndex, setLineIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);

  useEffect(() => {
    if (reduce) return;

    const line = LINES[lineIndex];
    if (charIndex < line.length) {
      const t = window.setTimeout(() => setCharIndex((c) => c + 1), 26);
      return () => window.clearTimeout(t);
    }
    const hold = window.setTimeout(() => {
      setLineIndex((i) => (i + 1) % LINES.length);
      setCharIndex(0);
    }, 2100);
    return () => window.clearTimeout(hold);
  }, [lineIndex, charIndex, reduce]);

  const display = reduce ? LINES[LINES.length - 1]! : LINES[lineIndex]!.slice(0, charIndex);
  const cursor = !reduce && charIndex >= LINES[lineIndex]!.length ? " █" : !reduce ? "▍" : "";

  return (
    <div
      className="mt-5 overflow-hidden rounded-xl border border-slate-800/90 bg-black/80 shadow-lg shadow-black/40 ring-1 ring-white/[0.06] backdrop-blur-sm"
      aria-label="Bot status console"
    >
      <div className="flex items-center justify-between gap-2 border-b border-slate-800/80 bg-slate-950/80 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="flex gap-1.5" aria-hidden>
            <span className="h-2 w-2 rounded-full bg-rose-500/90" />
            <span className="h-2 w-2 rounded-full bg-amber-400/90" />
            <span className="h-2 w-2 rounded-full bg-emerald-500/80" />
          </span>
          <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500">executor</span>
        </div>
        <div className="flex items-center gap-1.5">
          <motion.span
            className="relative flex h-2 w-2"
            aria-hidden
            animate={
              reduce
                ? undefined
                : {
                    opacity: [0.45, 1, 0.45],
                    scale: [1, 1.05, 1],
                  }
            }
            transition={
              reduce
                ? undefined
                : { duration: 1.6, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }
            }
          >
            <span className="absolute inset-0 rounded-full bg-emerald-400 blur-[3px] opacity-70" />
            <span className="relative block h-2 w-2 rounded-full bg-emerald-400 ring-1 ring-emerald-300/50" />
          </motion.span>
          <span className="font-mono text-[10px] font-medium uppercase tracking-wide text-emerald-400/95">Online</span>
        </div>
      </div>
      <div className="min-h-[2.75rem] px-3 py-3 font-mono text-[11px] leading-relaxed text-emerald-100/90 sm:min-h-[3rem] sm:text-xs">
        <span className="whitespace-pre-wrap break-all">{display}</span>
        {!reduce ? <span className="text-emerald-400/80">{cursor}</span> : null}
      </div>
    </div>
  );
}
