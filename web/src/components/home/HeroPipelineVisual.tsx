"use client";

import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import {
  Cloud,
  KeyRound,
  LayoutDashboard,
  Lock,
  Monitor,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";

const MAX_TILT = 5;

function useFinePointer() {
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine) and (min-width: 1024px)");
    const sync = () => setFine(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return fine;
}

/* ─── Animated vertical connector ─── */
function VConnector({
  delay,
  tone = "sky",
}: {
  delay: number;
  tone?: "sky" | "emerald";
}) {
  const reduce = useReducedMotion();
  const id = useId();
  const color = tone === "sky" ? "rgba(56,189,248,0.9)" : "rgba(0,230,118,0.9)";
  const mid = tone === "sky" ? "rgba(56,189,248,0.5)" : "rgba(0,230,118,0.5)";

  return (
    <div className="flex justify-center py-1.5" aria-hidden>
      <svg width="2" height="32" viewBox="0 0 2 32" className="overflow-visible">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={mid} stopOpacity="0.3" />
            <stop offset="50%" stopColor={color} />
            <stop offset="100%" stopColor={mid} stopOpacity="0.3" />
          </linearGradient>
        </defs>
        <line x1="1" y1="0" x2="1" y2="32" stroke="rgba(255,255,255,0.07)" strokeWidth="2" />
        <motion.line
          x1="1"
          y1="0"
          x2="1"
          y2="32"
          stroke={`url(#${id})`}
          strokeWidth="2"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.55, delay, ease: "easeOut" }}
        />
        {!reduce && (
          <motion.circle
            cx="1"
            r="2.5"
            fill={tone === "sky" ? "#38bdf8" : "#00e676"}
            style={{ filter: `drop-shadow(0 0 5px ${tone === "sky" ? "#38bdf8" : "#00e676"})` }}
            initial={{ cy: 2, opacity: 0 }}
            animate={{ cy: [2, 30, 2], opacity: [0, 1, 1, 0] }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              ease: "easeInOut",
              delay: delay + 0.5,
            }}
          />
        )}
      </svg>
    </div>
  );
}

/* ─── Single pipeline node ─── */
function PipeNode({
  icon: Icon,
  label,
  desc,
  tone,
  delay,
  isLast = false,
}: {
  icon: typeof Cloud;
  label: string;
  desc: string;
  tone: "sky" | "emerald" | "neutral";
  delay: number;
  isLast?: boolean;
}) {
  const toneStyles = {
    sky: {
      wrap: "border-sky-500/30 bg-sky-500/[0.08] hover:border-sky-400/50 hover:bg-sky-500/[0.12]",
      icon: "bg-sky-500/20 border-sky-400/30 text-sky-300",
      dot: "bg-sky-400",
    },
    emerald: {
      wrap: "border-emerald-500/35 bg-emerald-500/[0.08] hover:border-emerald-400/55 hover:bg-emerald-500/[0.13]",
      icon: "bg-emerald-500/20 border-emerald-400/30 text-emerald-300",
      dot: "bg-emerald-400",
    },
    neutral: {
      wrap: "border-white/10 bg-white/[0.04] hover:border-white/20 hover:bg-white/[0.07]",
      icon: "bg-white/[0.08] border-white/15 text-slate-300",
      dot: "bg-slate-400",
    },
  }[tone];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`group relative rounded-xl border px-3.5 py-3 transition-all duration-200 ${toneStyles.wrap}`}
    >
      {/* Subtle corner glint */}
      <div className="pointer-events-none absolute inset-0 rounded-xl bg-gradient-to-br from-white/[0.05] to-transparent opacity-0 transition-opacity duration-200 group-hover:opacity-100" />

      <div className="flex items-center gap-3">
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] ${toneStyles.icon}`}
        >
          <Icon className="h-4 w-4" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-none text-white">{label}</p>
          <p className="mt-1.5 text-[0.72rem] leading-relaxed text-slate-400">{desc}</p>
        </div>
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${toneStyles.dot} opacity-60`} />
      </div>
    </motion.div>
  );
}

/* ─── Horizontal signal arrow crossing the boundary ─── */
function CrossBoundaryArrow() {
  const reduce = useReducedMotion();
  const id = useId();

  return (
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 top-0 flex items-center justify-center" aria-hidden>
      <svg
        className="absolute"
        style={{ left: "calc(50% - 56px)", width: 112, height: 32, top: "calc(50% - 16px)" }}
        viewBox="0 0 112 32"
        overflow="visible"
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(56,189,248,0)" />
            <stop offset="30%" stopColor="rgba(56,189,248,0.7)" />
            <stop offset="70%" stopColor="rgba(0,230,118,0.7)" />
            <stop offset="100%" stopColor="rgba(0,230,118,0)" />
          </linearGradient>
        </defs>
        <motion.path
          d="M4 16 L108 16"
          fill="none"
          stroke={`url(#${id})`}
          strokeWidth="1.5"
          strokeDasharray="5 4"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.7 }}
        />
        <path d="M104 12 L112 16 L104 20" fill="none" stroke="rgba(0,230,118,0.6)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        {!reduce && (
          <motion.circle
            cy="16"
            r="2"
            fill="url(#hpv-cross-fill)"
            style={{ filter: "drop-shadow(0 0 4px rgba(0,230,118,0.8))" }}
            initial={{ cx: 4, opacity: 0 }}
            animate={{ cx: [4, 108, 4], opacity: [0, 1, 1, 0] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
          />
        )}
        <defs>
          <linearGradient id="hpv-cross-fill" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#00e676" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

/* ─── Main component ─── */
export function HeroPipelineVisual() {
  const zoneRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const finePointer = useFinePointer();
  const enableTilt = finePointer && !reduce;

  const nx = useMotionValue(0);
  const ny = useMotionValue(0);
  const rotateX = useSpring(useTransform(ny, [-1, 1], [MAX_TILT, -MAX_TILT]), { stiffness: 260, damping: 36 });
  const rotateY = useSpring(useTransform(nx, [-1, 1], [-MAX_TILT, MAX_TILT]), { stiffness: 260, damping: 36 });
  const glowX = useSpring(50, { stiffness: 280, damping: 34 });
  const glowY = useSpring(42, { stiffness: 280, damping: 34 });

  const onMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = zoneRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      nx.set(px * 2 - 1);
      ny.set(py * 2 - 1);
      glowX.set(px * 100);
      glowY.set(py * 100);
    },
    [nx, ny, glowX, glowY],
  );

  const onMouseLeave = useCallback(() => {
    nx.set(0);
    ny.set(0);
    glowX.set(50);
    glowY.set(42);
  }, [nx, ny, glowX, glowY]);

  const sheen = useMotionTemplate`radial-gradient(280px 200px at ${glowX}% ${glowY}%, rgba(255,255,255,0.09), transparent 65%)`;

  return (
    <div
      ref={zoneRef}
      className="relative mx-auto w-full max-w-[560px] select-none lg:mx-0 lg:max-w-none"
      onMouseMove={enableTilt ? onMouseMove : undefined}
      onMouseLeave={enableTilt ? onMouseLeave : undefined}
    >
      {/* Ambient glow halo behind card */}
      <div
        className="pointer-events-none absolute -inset-6 rounded-[2.5rem] opacity-70 blur-3xl"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 30% 50%, rgba(56,189,248,0.12), transparent 55%), radial-gradient(ellipse 80% 60% at 70% 50%, rgba(0,230,118,0.14), transparent 55%)",
        }}
        aria-hidden
      />

      <motion.div
        className="relative overflow-hidden rounded-2xl border border-white/[0.1] bg-[#050506] shadow-[0_24px_64px_-24px_rgba(0,0,0,0.9),inset_0_1px_0_rgba(255,255,255,0.06)] motion-reduce:transform-none"
        style={{
          rotateX: enableTilt ? rotateX : 0,
          rotateY: enableTilt ? rotateY : 0,
          transformPerspective: 1200,
          transformStyle: "preserve-3d",
        }}
        aria-label="SwiftTrade architecture: web portal and cloud signals on the left, desktop executor and Trading212 on the right"
      >
        {/* Interactive cursor sheen */}
        {enableTilt && (
          <motion.div
            className="pointer-events-none absolute inset-0 z-[1] opacity-60"
            style={{ background: sheen }}
            aria-hidden
          />
        )}

        {/* ── Top chrome bar ── */}
        <div className="relative z-10 flex items-center justify-between border-b border-white/[0.07] bg-white/[0.025] px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/50 motion-reduce:animate-none" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(0,230,118,0.7)]" />
            </div>
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-slate-400">
              How it works
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1">
            <Zap className="h-3 w-3 text-emerald-400" strokeWidth={2.5} />
            <span className="text-[0.62rem] font-semibold text-emerald-300">Live signals</span>
          </div>
        </div>

        {/* ── Two-column body ── */}
        <div className="relative grid grid-cols-[1fr_auto_1fr]">
          {/* Left: Cloud zone */}
          <div className="relative overflow-hidden px-4 py-5">
            {/* Subtle sky tint on this half */}
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.35]"
              style={{
                background: "radial-gradient(ellipse 120% 100% at 50% 0%, rgba(56,189,248,0.12), transparent 70%)",
              }}
              aria-hidden
            />

            <motion.p
              className="mb-3.5 flex items-center gap-1.5 text-[0.62rem] font-bold uppercase tracking-[0.2em] text-sky-400/90"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.05 }}
            >
              <Cloud className="h-3 w-3" strokeWidth={2.5} />
              Cloud
            </motion.p>

            <PipeNode
              icon={LayoutDashboard}
              label="Web portal"
              desc="Account, subscription & license key"
              tone="sky"
              delay={0.1}
            />

            <VConnector delay={0.22} tone="sky" />

            <PipeNode
              icon={Cloud}
              label="Signal feed"
              desc="Supabase Realtime — no broker keys"
              tone="sky"
              delay={0.3}
            />

            {/* Bottom zone footnote */}
            <motion.p
              className="mt-3.5 text-center text-[0.62rem] text-slate-600"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.55 }}
            >
              🔒 No API keys here
            </motion.p>
          </div>

          {/* Center divider — security boundary */}
          <div className="relative flex w-[2px] flex-col items-center justify-center">
            {/* The glowing line itself */}
            <motion.div
              className="h-full w-[1.5px]"
              style={{
                background:
                  "linear-gradient(to bottom, transparent 0%, rgba(251,191,36,0.25) 15%, rgba(251,191,36,0.6) 35%, rgba(251,191,36,0.6) 65%, rgba(251,191,36,0.25) 85%, transparent 100%)",
              }}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
            />

            {/* Lock badge pinned to the center */}
            <motion.div
              className="absolute flex flex-col items-center"
              style={{ top: "50%", transform: "translateY(-50%)" }}
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35, delay: 0.65, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-400/40 bg-[#0a090a] shadow-[0_0_16px_-4px_rgba(251,191,36,0.5)]">
                <Lock className="h-3.5 w-3.5 text-amber-300" strokeWidth={2} />
              </div>
              {/* Pulsing glow ring */}
              {!reduce && (
                <motion.div
                  className="pointer-events-none absolute h-8 w-8 rounded-full border border-amber-400/30"
                  animate={{ scale: [1, 1.6, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                  aria-hidden
                />
              )}
              {/* Rotated label */}
              <span
                className="mt-1.5 text-[0.55rem] font-bold uppercase tracking-[0.22em] text-amber-400/70"
                style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", letterSpacing: "0.18em" }}
              >
                Security boundary
              </span>
            </motion.div>
          </div>

          {/* Right: Local zone */}
          <div className="relative overflow-hidden px-4 py-5">
            {/* Subtle emerald tint on this half */}
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.35]"
              style={{
                background:
                  "radial-gradient(ellipse 120% 100% at 50% 0%, rgba(16,185,129,0.12), transparent 70%)",
              }}
              aria-hidden
            />

            <motion.p
              className="mb-3.5 flex items-center gap-1.5 text-[0.62rem] font-bold uppercase tracking-[0.2em] text-emerald-400/90"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.05 }}
            >
              <Monitor className="h-3 w-3" strokeWidth={2.5} />
              Your PC
            </motion.p>

            <PipeNode
              icon={Monitor}
              label="Desktop app"
              desc="API key stored here only — never sent out"
              tone="emerald"
              delay={0.1}
            />

            <VConnector delay={0.22} tone="emerald" />

            <PipeNode
              icon={TrendingUp}
              label="Trading212"
              desc="Orders placed from your machine"
              tone="neutral"
              delay={0.3}
              isLast
            />

            {/* Bottom zone footnote */}
            <motion.p
              className="mt-3.5 text-center text-[0.62rem] text-slate-600"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.55 }}
            >
              ✓ Keys live here
            </motion.p>
          </div>
        </div>

        {/* ── Bottom summary bar ── */}
        <div className="relative z-10 border-t border-white/[0.07] bg-white/[0.015] px-5 py-3">
          <div className="flex items-center justify-center gap-3">
            <span className="flex items-center gap-1.5 text-[0.65rem] text-slate-500">
              <span className="inline-block h-2 w-2 rounded-full bg-sky-400/70" />
              Portal manages your subscription
            </span>
            <span className="text-slate-700">·</span>
            <span className="flex items-center gap-1.5 text-[0.65rem] text-slate-500">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400/70" />
              Desktop talks to Trading212
            </span>
          </div>

          {/* Animated signal crossing label */}
          <motion.div
            className="mt-1.5 flex items-center justify-center gap-1 text-[0.6rem] text-slate-600"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9 }}
          >
            <KeyRound className="h-3 w-3 text-amber-500/60" />
            <span>Signals cross · API keys never do</span>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
