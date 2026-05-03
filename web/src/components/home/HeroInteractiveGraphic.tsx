"use client";

/**
 * HeroInteractiveGraphic — premium glass hero visual: tilt card, ambient glow,
 * abstract execution stream. Pills are clipped to the chart band so they never
 * clutter the chrome row (addresses overlapping “noise” in earlier iterations).
 */

import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";

/** Max tilt in degrees — restrained for institutional feel */
const MAX_TILT_DEG = 10;

const tiltSpring = { stiffness: 300, damping: 36, mass: 0.82 };

const orbSpring = { stiffness: 52, damping: 24, mass: 1.05 };

/** Spotlight inside the glass follows pointer (desktop only), separate from orb */
const spotlightSpring = { stiffness: 320, damping: 38, mass: 0.75 };

/**
 * Fewer, wider-spaced pills rising only through the chart zone — reads calmer
 * than eight overlapping chips fighting the header.
 */
const FLOW_PILLS = [
  { id: "a", xPct: 10, delay: 0, duration: 12.5, tone: "green" as const, w: 56 },
  { id: "b", xPct: 28, delay: 2.2, duration: 10.8, tone: "red" as const, w: 52 },
  { id: "c", xPct: 48, delay: 1.0, duration: 13.2, tone: "green" as const, w: 60 },
  { id: "d", xPct: 68, delay: 3.6, duration: 11.4, tone: "red" as const, w: 54 },
  { id: "e", xPct: 86, delay: 4.8, duration: 12.0, tone: "green" as const, w: 58 },
  { id: "f", xPct: 38, delay: 6.5, duration: 10.2, tone: "red" as const, w: 50 },
] as const;

const SPARK_PATHS: Record<string, string> = {
  a: "M0 6 L7 3 L14 7 L21 2 L28 5 L35 3 L42 6",
  b: "M0 4 L8 7 L16 3 L24 6 L32 2 L40 5 L48 4",
  c: "M0 7 L9 4 L18 8 L27 3 L36 6 L45 2 L54 5",
  default: "M0 7 L6 3 L12 6 L18 2 L24 5 L30 1 L36 4",
};

function useFinePointer() {
  const [fine, setFine] = useState(true);

  useEffect(() => {
    const mqHover = window.matchMedia("(hover: hover) and (pointer: fine)");
    const mqWide = window.matchMedia("(min-width: 1024px)");

    const sync = () => setFine(mqHover.matches && mqWide.matches);
    sync();
    mqHover.addEventListener("change", sync);
    mqWide.addEventListener("change", sync);
    return () => {
      mqHover.removeEventListener("change", sync);
      mqWide.removeEventListener("change", sync);
    };
  }, []);

  return fine;
}

function MicroSpark({ tone, variant }: { tone: "green" | "red"; variant: string }) {
  const stroke = tone === "green" ? "rgba(139,92,246,0.92)" : "rgba(251,113,133,0.88)";
  const d = SPARK_PATHS[variant] ?? SPARK_PATHS.default;
  return (
    <svg width="40" height="10" viewBox="0 0 42 10" aria-hidden className="shrink-0 opacity-95">
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function HeroInteractiveGraphic() {
  const zoneRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const finePointer = useFinePointer();
  const enableTilt = finePointer && !reduceMotion;

  const nx = useMotionValue(0);
  const ny = useMotionValue(0);

  const rotateX = useSpring(
    useTransform(ny, [-1, 1], [MAX_TILT_DEG, -MAX_TILT_DEG]),
    tiltSpring,
  );
  const rotateY = useSpring(
    useTransform(nx, [-1, 1], [-MAX_TILT_DEG, MAX_TILT_DEG]),
    tiltSpring,
  );

  const orbX = useSpring(50, orbSpring);
  const orbY = useSpring(42, orbSpring);

  /** Cursor position as % inside card for frosted highlight (Feature polish) */
  const glowX = useSpring(50, spotlightSpring);
  const glowY = useSpring(45, spotlightSpring);

  const onMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = zoneRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      nx.set(px * 2 - 1);
      ny.set(py * 2 - 1);
      orbX.set(10 + px * 80);
      orbY.set(12 + py * 76);

      // Map same pointer into card-local highlight space
      glowX.set(px * 100);
      glowY.set(py * 100);
    },
    [nx, ny, orbX, orbY, glowX, glowY],
  );

  const onMouseLeave = useCallback(() => {
    nx.set(0);
    ny.set(0);
    orbX.set(50);
    orbY.set(42);
    glowX.set(50);
    glowY.set(45);
  }, [nx, ny, orbX, orbY, glowX, glowY]);

  const orbBackground = useMotionTemplate`radial-gradient(460px 340px at ${orbX}% ${orbY}%, rgba(139,92,246,0.4), rgba(99,102,241,0.16) 36%, transparent 70%)`;

  /** Soft moving highlight on the glass surface — reads “alive” without clutter */
  const cardSheen = useMotionTemplate`radial-gradient(280px 220px at ${glowX}% ${glowY}%, rgba(255,255,255,0.14), transparent 62%)`;

  const svgUid = "heroGfx";

  return (
    <div
      ref={zoneRef}
      className="relative isolate mx-auto aspect-[4/3] w-full max-w-lg select-none lg:mx-0 lg:max-w-none lg:aspect-[5/4]"
      onMouseMove={enableTilt ? onMouseMove : undefined}
      onMouseLeave={enableTilt ? onMouseLeave : undefined}
    >
      {/* Ambient field behind entire widget */}
      <motion.div
        className="pointer-events-none absolute inset-0 -z-10 rounded-[2rem] opacity-[0.22] blur-3xl motion-reduce:opacity-[0.12]"
        style={{ background: orbBackground }}
        aria-hidden
      />

      {/* Secondary softer halo for depth */}
      <div
        className="pointer-events-none absolute inset-[10%] -z-10 rounded-[1.75rem] bg-gradient-to-b from-violet-500/[0.07] to-transparent blur-2xl"
        aria-hidden
      />

      <motion.div
        className="relative z-10 mx-auto flex h-full min-h-[288px] max-w-md flex-col overflow-hidden rounded-3xl motion-reduce:transform-none lg:min-h-[332px]"
        style={{
          rotateX: enableTilt ? rotateX : 0,
          rotateY: enableTilt ? rotateY : 0,
          transformPerspective: 1200,
          transformStyle: "preserve-3d",
        }}
      >
        {/* Depth shadow + inset highlight ring (premium glass edge) */}
        <div
          className="pointer-events-none absolute inset-0 rounded-3xl shadow-[0_24px_48px_-28px_rgba(0,0,0,0.85)] ring-1 ring-inset ring-white/[0.09]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-px rounded-[calc(1.5rem-2px)] bg-gradient-to-br from-white/[0.07] via-transparent to-indigo-700/[0.05] opacity-90"
          aria-hidden
        />

        {/* Deal-flow lane: clipped to chart band only — no overlap with “Live engine” row */}
        <div className="pointer-events-none absolute inset-x-3 top-[26%] bottom-[22%] overflow-hidden rounded-xl motion-reduce:opacity-35">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/25 to-background/50" aria-hidden />
          {FLOW_PILLS.map((p) => (
            <motion.div
              key={p.id}
              className={`absolute flex h-[26px] items-center justify-center rounded-full border shadow-lg backdrop-blur-md ${
                p.tone === "green"
                  ? "border-violet-400/30 bg-violet-500/[0.12] shadow-violet-500/15"
                  : "border-rose-400/25 bg-rose-500/[0.11] shadow-rose-500/12"
              }`}
              style={{
                left: `calc(${p.xPct}% - ${p.w / 2}px)`,
                width: p.w,
              }}
              initial={false}
              animate={
                reduceMotion
                  ? { y: "62%", opacity: 0.22 }
                  : { y: ["102%", "-18%"], opacity: [0, 0.72, 0.68, 0] }
              }
              transition={
                reduceMotion
                  ? undefined
                  : {
                      duration: p.duration,
                      repeat: Number.POSITIVE_INFINITY,
                      ease: "easeOut" as const,
                      delay: p.delay,
                      repeatDelay: 0.35,
                    }
              }
              aria-hidden
            >
              <div className="flex w-full items-center justify-center gap-1 px-2">
                <span className="h-px w-2.5 rounded-full bg-white/40" />
                <MicroSpark tone={p.tone} variant={p.id} />
                <span className="h-px w-2.5 rounded-full bg-white/30" />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Glass body */}
        <div className="relative flex h-full flex-col bg-background/[0.58] p-6 backdrop-blur-xl">
          {/* Interactive sheen (desktop); static gentle gradient when reduced motion */}
          {!reduceMotion && enableTilt ? (
            <motion.div
              className="pointer-events-none absolute inset-0 opacity-80 mix-blend-overlay"
              style={{ background: cardSheen }}
              aria-hidden
            />
          ) : (
            <div
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_90%_70%_at_50%_0%,rgba(255,255,255,0.06),transparent_55%)]"
              aria-hidden
            />
          )}

          {/* Chrome header — opaque enough that nothing bleeds through */}
          <div className="relative z-[2] flex items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400/35 opacity-70 motion-reduce:animate-none" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-400 shadow-[0_0_12px_2px_rgba(139,92,246,0.55)] ring-2 ring-indigo-400/35" />
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
                Live engine
              </span>
            </div>
            <div className="flex gap-1.5 opacity-60">
              <span className="h-1 w-1 rounded-full bg-white/25" />
              <span className="h-1 w-1 rounded-full bg-white/25" />
              <span className="h-1 w-1 rounded-full bg-white/25" />
            </div>
          </div>

          {/* Chart well */}
          <div className="relative z-[1] mt-5 flex min-h-[140px] flex-1 flex-col rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900 to-[#09090b] p-4 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]">
            <svg viewBox="0 0 280 120" className="h-[118px] w-full shrink-0" preserveAspectRatio="none" aria-hidden>
              <defs>
                <linearGradient id={`${svgUid}-fill`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
                  <stop offset="42%" stopColor="#f43f5e" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#09090b" stopOpacity="0" />
                </linearGradient>
                <linearGradient id={`${svgUid}-stroke`} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#6366f1" />
                  <stop offset="50%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
                <filter id={`${svgUid}-glow`} x="-40%" y="-40%" width="180%" height="180%">
                  <feGaussianBlur stdDeviation="2.2" result="b" />
                  <feMerge>
                    <feMergeNode in="b" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <motion.path
                d="M0 95 C40 88, 70 100, 100 72 S160 40, 200 55 S250 28, 280 22 L280 120 L0 120 Z"
                fill={`url(#${svgUid}-fill)`}
                initial={{ opacity: 0.5 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.45 }}
              />
              <motion.path
                d="M0 95 C40 88, 70 100, 100 72 S160 40, 200 55 S250 28, 280 22"
                fill="none"
                stroke={`url(#${svgUid}-stroke)`}
                strokeWidth="5"
                strokeLinecap="round"
                opacity="0.35"
                filter={`url(#${svgUid}-glow)`}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={reduceMotion ? { duration: 0 } : { duration: 1.45, ease: "easeOut" }}
              />
              <motion.path
                d="M0 95 C40 88, 70 100, 100 72 S160 40, 200 55 S250 28, 280 22"
                fill="none"
                stroke={`url(#${svgUid}-stroke)`}
                strokeWidth="2.25"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={reduceMotion ? { duration: 0 } : { duration: 1.45, ease: "easeOut" }}
              />
            </svg>

            <div
              className="pointer-events-none absolute inset-4 rounded-lg opacity-[0.055]"
              style={{
                backgroundImage:
                  "linear-gradient(to right, rgba(255,255,255,0.9) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.9) 1px, transparent 1px)",
                backgroundSize: "24px 20px",
              }}
              aria-hidden
            />

            {/* Very subtle scan shimmer */}
            {!reduceMotion ? (
              <motion.div
                className="pointer-events-none absolute inset-y-5 w-[28%] rounded-full bg-gradient-to-r from-transparent via-white/[0.07] to-transparent blur-[2px]"
                initial={{ left: "-18%" }}
                animate={{ left: "112%" }}
                transition={{ duration: 6.5, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut", repeatDelay: 2.5 }}
                aria-hidden
              />
            ) : null}
          </div>

          {/* Footer */}
          <div className="relative z-[2] mt-5 flex items-end justify-between gap-4 pt-1">
            <div className="space-y-2.5">
              <motion.div
                className="h-1 w-[5.5rem] rounded-full bg-gradient-to-r from-violet-400/35 to-white/10"
                initial={false}
                animate={reduceMotion ? { opacity: 0.85 } : { opacity: [0.55, 1, 0.55] }}
                transition={
                  reduceMotion ? undefined : { duration: 3.2, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }
                }
              />
              <div className="h-1 w-14 rounded-full bg-white/[0.09]" />
            </div>
            <div className="flex h-[52px] items-end gap-[5px]">
              {[20, 34, 24, 42, 28].map((h, i) => (
                <motion.div
                  key={i}
                  className="w-[7px] rounded-[3px] bg-gradient-to-t from-slate-800 via-violet-600/45 to-indigo-600/55 shadow-[0_0_12px_-4px_rgba(139,92,246,0.35)]"
                  style={{ height: h }}
                  initial={false}
                  animate={reduceMotion ? { opacity: 0.9 } : { opacity: [0.72, 1, 0.72] }}
                  transition={
                    reduceMotion
                      ? undefined
                      : {
                          duration: 2.4 + i * 0.15,
                          repeat: Number.POSITIVE_INFINITY,
                          ease: "easeInOut",
                          delay: i * 0.12,
                        }
                  }
                />
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
