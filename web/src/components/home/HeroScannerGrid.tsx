"use client";

/**
 * HeroScannerGrid — isometric scanner backdrop with sweep + sparse signal cells.
 * Signal updates use functional setState only (never depend on `signals` in useEffect)
 * so we avoid infinite re-run loops.
 */

import { motion, useReducedMotion } from "framer-motion";
import { type CSSProperties, useEffect, useMemo, useState } from "react";

const COLS = 20;
const ROWS = 10;
const CELL_PX = 11;
const GAP_PX = 1;

const MAX_SIGNALS = 4;
const SIGNAL_HOLD_MS_MIN = 1000;
const SIGNAL_HOLD_MS_MAX = 2000;
const SIGNAL_TICK_MS = 550;

function cellKey(c: number, r: number) {
  return `${c},${r}`;
}

function randomInt(max: number) {
  return Math.floor(Math.random() * max);
}

type SignalEntry = { hue: "core" | "neon"; expiresAt: number };

function signalsEqual(a: Record<string, SignalEntry>, b: Record<string, SignalEntry>) {
  const ak = Object.keys(a).sort().join("|");
  const bk = Object.keys(b).sort().join("|");
  if (ak !== bk) return false;
  for (const k of Object.keys(a)) {
    if (a[k].expiresAt !== b[k].expiresAt || a[k].hue !== b[k].hue) return false;
  }
  return true;
}

export function HeroScannerGrid() {
  const reduceMotion = useReducedMotion();
  const [scanCol, setScanCol] = useState(0);
  const [signals, setSignals] = useState<Record<string, SignalEntry>>({});

  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(() => {
      setScanCol((c) => (c + 1) % COLS);
    }, 140);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  useEffect(() => {
    if (reduceMotion) return;

    const tick = () => {
      setSignals((prev) => {
        const now = Date.now();
        const next: Record<string, SignalEntry> = { ...prev };

        for (const [k, v] of Object.entries(next)) {
          if (v.expiresAt <= now) delete next[k];
        }

        let attempts = 0;
        while (Object.keys(next).length < MAX_SIGNALS && attempts < 120) {
          attempts += 1;
          const c = randomInt(COLS);
          const r = randomInt(ROWS);
          const k = cellKey(c, r);
          if (next[k]) continue;
          next[k] = {
            hue: Math.random() > 0.45 ? "neon" : "core",
            expiresAt: now + SIGNAL_HOLD_MS_MIN + randomInt(SIGNAL_HOLD_MS_MAX - SIGNAL_HOLD_MS_MIN + 1),
          };
        }

        if (signalsEqual(prev, next)) return prev;
        return next;
      });
    };

    tick();
    const id = window.setInterval(tick, SIGNAL_TICK_MS);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  const gridTemplate = useMemo(
    () => ({
      gridTemplateColumns: `repeat(${COLS}, ${CELL_PX}px)`,
      gridTemplateRows: `repeat(${ROWS}, ${CELL_PX}px)`,
      gap: `${GAP_PX}px`,
    }),
    [],
  );

  const scanWaveTransition = reduceMotion
    ? undefined
    : { duration: 14, repeat: Number.POSITIVE_INFINITY, ease: "linear" as const };

  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0 z-0 h-[380px] overflow-hidden sm:h-[440px] lg:h-[500px]"
      aria-hidden
    >
      <div
        className="absolute inset-0 [-webkit-mask-image:linear-gradient(to_bottom,black_25%,black_50%,transparent_92%),linear-gradient(to_right,transparent_0%,black_12%,black_88%,transparent_100%)] [-webkit-mask-composite:source-in] [mask-image:linear-gradient(to_bottom,black_25%,black_50%,transparent_92%),linear-gradient(to_right,transparent_0%,black_12%,black_88%,transparent_100%)] [mask-composite:intersect]"
        style={
          {
            WebkitMaskComposite: "source-in",
          } as CSSProperties
        }
      >
        <div
          className="absolute left-1/2 top-[52%] flex h-[min(90vw,720px)] w-[min(92vw,780px)] -translate-x-1/2 -translate-y-1/2 items-center justify-center"
          style={{ perspective: 1400 }}
        >
          <div
            className="relative will-change-transform"
            style={{
              transform: "rotateX(60deg) rotateZ(-45deg)",
              transformStyle: "preserve-3d",
            }}
          >
            {!reduceMotion ? (
              <motion.div
                className="pointer-events-none absolute -left-[40%] top-0 z-10 h-full w-[42%] opacity-[0.85]"
                initial={{ x: "-20%" }}
                animate={{ x: "340%" }}
                transition={scanWaveTransition}
                style={{
                  background:
                    "linear-gradient(90deg, transparent 0%, rgba(16,185,129,0.07) 35%, rgba(16,185,129,0.22) 50%, rgba(0,230,118,0.14) 65%, transparent 100%)",
                  mixBlendMode: "screen",
                }}
              />
            ) : null}

            <div className="relative grid" style={gridTemplate}>
              {Array.from({ length: ROWS * COLS }, (_, i) => {
                const r = Math.floor(i / COLS);
                const c = i % COLS;
                const k = cellKey(c, r);
                const sig = signals[k];
                const scanHit = !reduceMotion && c === scanCol;

                const signalStyles =
                  sig?.hue === "neon"
                    ? "border-[#00E676]/50 bg-[#00E676]/[0.12] shadow-[0_0_14px_-2px_rgba(0,230,118,0.55)]"
                    : sig?.hue === "core"
                      ? "border-emerald-500/50 bg-emerald-500/[0.14] shadow-[0_0_14px_-2px_rgba(16,185,129,0.5)]"
                      : "";

                const scanStyles = scanHit
                  ? "border-emerald-400/35 shadow-[0_0_10px_-3px_rgba(16,185,129,0.38)]"
                  : "";

                return (
                  <div
                    key={k}
                    className={`rounded-[2px] border border-white/[0.06] bg-[#0A0A0A] transition-[border-color,box-shadow,background-color] duration-700 ease-out ${signalStyles} ${scanStyles}`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
