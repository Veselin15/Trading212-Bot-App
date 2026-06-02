"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import { useState } from "react";

// ── EU star ring geometry ──────────────────────────────────────────────────
// SVG viewBox is "0 0 100 100". Star circle centre ≈ 50% x, 51% y of image.
const SC = { x: 50, y: 51 };
const SR = { x: 12.5, y: 13.5 }; // slightly elliptical to match map projection

function starPolygonPoints(cx: number, cy: number, r: number): string {
  const pts: string[] = [];
  const inner = r * 0.4;
  for (let i = 0; i < 5; i++) {
    const a1 = (i * 72 - 90) * (Math.PI / 180);
    const a2 = a1 + 36 * (Math.PI / 180);
    pts.push(`${(cx + r * Math.cos(a1)).toFixed(3)},${(cy + r * Math.sin(a1)).toFixed(3)}`);
    pts.push(`${(cx + inner * Math.cos(a2)).toFixed(3)},${(cy + inner * Math.sin(a2)).toFixed(3)}`);
  }
  return pts.join(" ");
}

const EU_STARS = Array.from({ length: 12 }, (_, i) => {
  const angle = (i * 30 - 90) * (Math.PI / 180);
  const cx = SC.x + SR.x * Math.cos(angle);
  const cy = SC.y + SR.y * Math.sin(angle);
  return {
    id: i,
    points: starPolygonPoints(cx, cy, 1.55),
    delay: (i * 0.065) % 0.8,
  };
});

// ── Key EU exchange city markers ───────────────────────────────────────────
// Approximate % positions on the map image
const EXCHANGES = [
  { id: "xetra",    city: "Frankfurt", exchange: "Xetra",    x: 53,   y: 33.5, color: "#10b981" },
  { id: "euronext", city: "Paris",     exchange: "Euronext", x: 41.5, y: 38.5, color: "#38bdf8" },
  { id: "ams",      city: "Amsterdam", exchange: "Euronext", x: 46.5, y: 28,   color: "#38bdf8" },
  { id: "milan",    city: "Milan",     exchange: "Borsa",    x: 53,   y: 44,   color: "#10b981" },
] as const;

const FOOTER_STATS = [
  { val: "27",   label: "EU states"   },
  { val: "1k+",  label: "EU stocks"   },
  { val: "0%",   label: "US dividend" },
];

export function EUMapHeroVisual() {
  const reduce = useReducedMotion();
  const [hovered, setHovered] = useState(false);

  return (
    <div className="relative mx-auto w-full max-w-[560px] select-none lg:mx-0 lg:max-w-none">
      {/* Ambient dual-colour halo — EU blue + emerald */}
      <motion.div
        className="pointer-events-none absolute -inset-8 rounded-[2.5rem] blur-3xl"
        animate={{
          opacity: hovered ? 0.7 : 0.42,
          background: hovered
            ? "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,51,153,0.5), rgba(16,185,129,0.20) 52%, transparent 76%)"
            : "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,51,153,0.32), rgba(16,185,129,0.10) 52%, transparent 76%)",
        }}
        transition={{ duration: 0.5 }}
        aria-hidden
      />

      <motion.div
        className="relative overflow-hidden rounded-2xl bg-[#02020c] shadow-[0_32px_80px_-24px_rgba(0,0,0,0.92),inset_0_1px_0_rgba(255,255,255,0.07)] motion-reduce:transform-none"
        style={{
          border: hovered ? "1px solid rgba(255,255,255,0.16)" : "1px solid rgba(255,255,255,0.10)",
          transition: "border-color 0.3s",
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* ── Chrome header ── */}
        <div className="relative z-10 flex items-center justify-between border-b border-white/[0.07] bg-white/[0.02] px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-2 w-2">
              {!reduce && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/50 motion-reduce:animate-none" />
              )}
              <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.88)]" />
            </div>
            <span className="text-[0.64rem] font-bold uppercase tracking-[0.22em] text-slate-400">
              EU-only universe
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-500/10 px-2.5 py-1">
            <span className="text-[0.6rem] font-bold text-amber-300">🇪🇺 EU member states only</span>
          </div>
        </div>

        {/* ── EU Map ── */}
        <div className="relative overflow-hidden" style={{ aspectRatio: "1 / 0.94" }}>
          {/* Base map image — darkened + slightly desaturated so the site's palette dominates */}
          <Image
            src="/eu-map.png"
            alt="European Union member states"
            fill
            className="object-contain"
            style={{ filter: "brightness(0.72) saturate(0.88)", opacity: 0.96 }}
            sizes="(max-width: 768px) 100vw, 560px"
            priority
          />

          {/* EU-blue centre glow — screen blend keeps the stars visible */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse 55% 50% at 50% 50%, rgba(0,40,120,0.28), transparent 68%)",
              mixBlendMode: "screen",
            }}
            aria-hidden
          />

          {/* Emerald edge glint — adds site-colour warmth */}
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse 90% 70% at 50% 80%, rgba(16,185,129,0.07), transparent 55%)",
            }}
            aria-hidden
          />

          {/* ── SVG overlay: stars + city pulse dots ── */}
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="xMidYMid meet"
            className="pointer-events-none absolute inset-0 h-full w-full"
            aria-hidden
          >
            <defs>
              <filter id="euStarGlow" x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="1.0" result="glow" />
                <feMerge>
                  <feMergeNode in="glow" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="euDotGlow" x="-200%" y="-200%" width="500%" height="500%">
                <feGaussianBlur stdDeviation="0.8" result="glow" />
                <feMerge>
                  <feMergeNode in="glow" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* 12 EU flag stars — twinkle in sequence */}
            {EU_STARS.map((s) => (
              <motion.polygon
                key={s.id}
                points={s.points}
                fill="#FFD700"
                filter="url(#euStarGlow)"
                initial={reduce ? {} : { opacity: 0 }}
                animate={
                  reduce
                    ? { opacity: 0.9 }
                    : { opacity: [0.55, 1, 0.55] }
                }
                transition={
                  reduce
                    ? {}
                    : {
                        duration: 2.2 + (s.id % 5) * 0.2,
                        repeat: Infinity,
                        delay: s.delay,
                        ease: "easeInOut",
                      }
                }
              />
            ))}

            {/* Exchange city pulse dots */}
            {EXCHANGES.map((ex, i) => (
              <g key={ex.id}>
                {!reduce && (
                  <motion.circle
                    cx={ex.x}
                    cy={ex.y}
                    r={1.2}
                    fill="none"
                    stroke={ex.color}
                    strokeWidth="0.4"
                    animate={{ r: [1.2, 5.5], opacity: [0.9, 0] }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      delay: i * 0.55,
                      ease: "easeOut",
                    }}
                  />
                )}
                <circle
                  cx={ex.x}
                  cy={ex.y}
                  r={0.9}
                  fill={ex.color}
                  filter="url(#euDotGlow)"
                />
              </g>
            ))}
          </svg>

          {/* Exchange city label chips */}
          {EXCHANGES.map((ex, i) => (
            <motion.div
              key={`lbl-${ex.id}`}
              className="pointer-events-none absolute"
              style={{
                left: `${ex.x}%`,
                top: `${ex.y}%`,
                transform: "translate(-50%, calc(-100% - 7px))",
              }}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55 + i * 0.12, duration: 0.3 }}
            >
              <div
                className="rounded-sm border border-white/[0.14] bg-black/82 px-1.5 py-[2px] backdrop-blur-sm"
                style={{ boxShadow: `0 0 8px -2px ${ex.color}66` }}
              >
                <p className="whitespace-nowrap font-mono text-[0.46rem] font-semibold leading-tight text-white/90">
                  {ex.city}
                </p>
              </div>
              {/* Connector line to dot */}
              <div
                className="mx-auto w-px"
                style={{ height: 6, background: `linear-gradient(to bottom, ${ex.color}88, transparent)` }}
              />
            </motion.div>
          ))}

          {/* Slow scan shimmer — gives the card an "alive" feel */}
          {!reduce && (
            <motion.div
              className="pointer-events-none absolute inset-y-0 w-[22%]"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.028), transparent)",
              }}
              initial={{ left: "-22%" }}
              animate={{ left: "122%" }}
              transition={{
                duration: 9,
                repeat: Infinity,
                ease: "easeInOut",
                repeatDelay: 3.5,
              }}
              aria-hidden
            />
          )}
        </div>

        {/* ── Footer stats bar ── */}
        <div className="relative z-10 border-t border-white/[0.07] bg-white/[0.015] px-5 py-3.5">
          <div className="flex items-center justify-around gap-2">
            {FOOTER_STATS.map((s, i) => (
              <div key={s.label} className="flex flex-1 flex-col items-center text-center">
                <motion.p
                  className="font-mono text-sm font-bold tabular-nums text-emerald-400"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.85 + i * 0.08, duration: 0.32 }}
                >
                  {s.val}
                </motion.p>
                <p className="text-[0.57rem] uppercase tracking-wide text-slate-600">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
