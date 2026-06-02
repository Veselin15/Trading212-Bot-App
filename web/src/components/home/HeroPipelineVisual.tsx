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
import { useCallback, useEffect, useRef, useState } from "react";

import { EUMapIcon } from "@/components/EUMapIcon";

const MAX_TILT = 4;
const EASE_SNAPPY = [0.22, 1, 0.36, 1] as const;

function useFinePointer() {
  const [fine, setFine] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(
      "(hover: hover) and (pointer: fine) and (min-width: 1024px)"
    );
    const sync = () => setFine(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return fine;
}

/* ─── Signal particle crossing the boundary ─── */
function SignalParticle({
  delay,
  duration = 1.15,
  repeatDelay = 4.5,
  size = 5,
  color = "#00e676",
}: {
  delay: number;
  duration?: number;
  repeatDelay?: number;
  size?: number;
  color?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return null;
  return (
    <motion.div
      className="pointer-events-none absolute"
      style={{
        top: `calc(50% - ${size / 2}px)`,
        left: `calc(50% - ${size / 2}px)`,
        height: size,
        width: size,
        borderRadius: "50%",
        backgroundColor: color,
        filter: `drop-shadow(0 0 ${size + 2}px ${color})`,
      }}
      initial={{ x: -48, opacity: 0 }}
      animate={{ x: [-48, 48], opacity: [0, 1, 1, 0] }}
      transition={{
        duration,
        delay,
        repeat: Infinity,
        repeatDelay,
        ease: "easeInOut",
        opacity: { times: [0, 0.1, 0.9, 1] },
      }}
      aria-hidden
    />
  );
}

/* ─── Vertical flow dot within a zone ─── */
function ZoneFlowDot({
  delay,
  tone,
  top,
}: {
  delay: number;
  tone: "sky" | "emerald";
  top: number;
}) {
  const reduce = useReducedMotion();
  if (reduce) return null;
  const color = tone === "sky" ? "#38bdf8" : "#00e676";
  return (
    <motion.div
      className="pointer-events-none absolute left-[22px]"
      style={{
        top,
        height: 4,
        width: 4,
        borderRadius: "50%",
        backgroundColor: color,
        filter: `drop-shadow(0 0 4px ${color})`,
      }}
      initial={{ y: 0, opacity: 0 }}
      animate={{ y: [0, 34, 34], opacity: [0, 1, 0] }}
      transition={{
        duration: 0.9,
        delay,
        repeat: Infinity,
        repeatDelay: 3.8,
        ease: "easeInOut",
        opacity: { times: [0, 0.15, 1] },
      }}
      aria-hidden
    />
  );
}

/* ─── Feature row with spotlight hover ─── */
function FeatureRow({
  id,
  icon: Icon,
  label,
  tone,
  delay,
  hoveredId,
  onHoverStart,
  onHoverEnd,
}: {
  id: string;
  icon: typeof Cloud;
  label: string;
  tone: "sky" | "emerald" | "neutral";
  delay: number;
  hoveredId: string | null;
  onHoverStart: (id: string) => void;
  onHoverEnd: () => void;
}) {
  const isSelf = hoveredId === id;
  const isDimmed = hoveredId !== null && !isSelf;

  const iconBase = {
    sky: "text-sky-400 bg-sky-500/15 border-sky-500/25",
    emerald: "text-emerald-400 bg-emerald-500/15 border-emerald-500/25",
    neutral: "text-slate-400 bg-white/[0.06] border-white/[0.1]",
  }[tone];

  const iconHover = {
    sky: "bg-sky-500/35 border-sky-400/55 shadow-[0_0_18px_-2px_rgba(56,189,248,0.7)]",
    emerald: "bg-emerald-500/35 border-emerald-400/55 shadow-[0_0_18px_-2px_rgba(0,230,118,0.7)]",
    neutral: "bg-white/[0.14] border-white/[0.22] shadow-[0_0_12px_-2px_rgba(255,255,255,0.3)]",
  }[tone];

  return (
    <motion.div
      className="group flex cursor-default items-center gap-3 rounded-xl px-2 py-1.5"
      animate={{
        opacity: isDimmed ? 0.28 : 1,
        x: isSelf ? 4 : 0,
        backgroundColor: isSelf ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0)",
      }}
      initial={{ opacity: 0, y: 8 }}
      transition={{
        opacity: { duration: isDimmed ? 0.18 : 0.3, delay: hoveredId ? 0 : delay },
        y: { duration: 0.32, delay, ease: EASE_SNAPPY },
        x: { duration: 0.2, ease: EASE_SNAPPY },
        backgroundColor: { duration: 0.18 },
      }}
      onHoverStart={() => onHoverStart(id)}
      onHoverEnd={onHoverEnd}
    >
      <motion.div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${isSelf ? iconHover : iconBase}`}
        animate={{ scale: isSelf ? 1.18 : 1 }}
        transition={{ duration: 0.18, ease: EASE_SNAPPY }}
      >
        <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
      </motion.div>
      <motion.span
        className="text-[0.79rem] leading-snug"
        animate={{ color: isSelf ? "#f8fafc" : isDimmed ? "#334155" : "#cbd5e1" }}
        transition={{ duration: 0.18 }}
      >
        {label}
      </motion.span>
    </motion.div>
  );
}

/* ─── Zone column wrapper ─── */
function Zone({
  side,
  icon: Icon,
  title,
  subtitle,
  tone,
  children,
  footerDot,
  footerText,
  hoveredZone,
  onEnter,
  onLeave,
}: {
  side: "left" | "right";
  icon: typeof Cloud;
  title: string;
  subtitle: string;
  tone: "sky" | "emerald";
  children: React.ReactNode;
  footerDot: string;
  footerText: string;
  hoveredZone: "left" | "right" | null;
  onEnter: () => void;
  onLeave: () => void;
}) {
  const isActive = hoveredZone === side;
  const isOther = hoveredZone !== null && !isActive;

  const tints = {
    sky: {
      bg: "rgba(56,189,248,0.22)",
      iconBorder: "border-sky-500/30",
      iconBg: "bg-sky-500/15",
      iconGlow: "rgba(56,189,248,0.45)",
      iconColor: "text-sky-300",
      zoneBorder: "rgba(56,189,248,0.18)",
    },
    emerald: {
      bg: "rgba(0,230,118,0.2)",
      iconBorder: "border-emerald-500/30",
      iconBg: "bg-emerald-500/15",
      iconGlow: "rgba(0,230,118,0.4)",
      iconColor: "text-emerald-300",
      zoneBorder: "rgba(0,230,118,0.16)",
    },
  }[tone];

  return (
    <motion.div
      className={`relative overflow-hidden p-5 ${side === "right" ? "border-l border-white/[0.05]" : ""}`}
      animate={{ opacity: isOther ? 0.7 : 1 }}
      transition={{ duration: 0.2 }}
      onHoverStart={onEnter}
      onHoverEnd={onLeave}
    >
      {/* Zone background tint — intensifies on hover */}
      <motion.div
        className="pointer-events-none absolute inset-0"
        animate={{
          opacity: isActive ? 1 : 0.18,
        }}
        transition={{ duration: 0.3 }}
        style={{
          background: `radial-gradient(ellipse 140% 90% at 50% 0%, ${tints.bg}, transparent 62%)`,
        }}
        aria-hidden
      />

      {/* Zone border glow on hover */}
      {isActive && (
        <motion.div
          className="pointer-events-none absolute inset-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{
            boxShadow: `inset 0 0 24px -8px ${tints.zoneBorder}`,
          }}
          aria-hidden
        />
      )}

      {/* Zone header */}
      <motion.div
        className="mb-5 flex items-center gap-3"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.08, ease: EASE_SNAPPY }}
      >
        {/* Floating icon */}
        <motion.div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${tints.iconBorder} ${tints.iconBg}`}
          style={{ boxShadow: `0 0 18px -4px ${tints.iconGlow}` }}
          animate={isActive
            ? { scale: 1.08, boxShadow: `0 0 28px -4px ${tints.iconGlow}` }
            : { scale: 1, boxShadow: `0 0 18px -4px ${tints.iconGlow}` }
          }
          transition={{ duration: 0.25, ease: EASE_SNAPPY }}
        >
          <motion.div
            animate={{ y: [0, -2, 0] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: side === "right" ? 1.2 : 0 }}
          >
            <Icon className={`h-4 w-4 ${tints.iconColor}`} strokeWidth={1.75} />
          </motion.div>
        </motion.div>
        <div>
          <p className="text-sm font-bold leading-tight text-white">{title}</p>
          <p className="text-[0.64rem] text-slate-600">{subtitle}</p>
        </div>
      </motion.div>

      {/* Feature rows */}
      <div className="relative space-y-1">
        {children}
      </div>

      {/* Footer note */}
      <motion.div
        className="mt-5 flex items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.55 }}
      >
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${footerDot}`} />
        <span className="text-[0.64rem] text-slate-600">{footerText}</span>
      </motion.div>
    </motion.div>
  );
}

/* ─── Main component ─── */
export function HeroPipelineVisual() {
  const zoneRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const finePointer = useFinePointer();
  const enableTilt = finePointer && !reduce;

  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [hoveredZone, setHoveredZone] = useState<"left" | "right" | null>(null);

  // Card tilt
  const nx = useMotionValue(0);
  const ny = useMotionValue(0);
  const rotateX = useSpring(useTransform(ny, [-1, 1], [MAX_TILT, -MAX_TILT]), { stiffness: 260, damping: 36 });
  const rotateY = useSpring(useTransform(nx, [-1, 1], [-MAX_TILT, MAX_TILT]), { stiffness: 260, damping: 36 });
  const glowX = useSpring(50, { stiffness: 280, damping: 34 });
  const glowY = useSpring(42, { stiffness: 280, damping: 34 });

  const onMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = zoneRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    nx.set(px * 2 - 1);
    ny.set(py * 2 - 1);
    glowX.set(px * 100);
    glowY.set(py * 100);
  }, [nx, ny, glowX, glowY]);

  const onMouseLeave = useCallback(() => {
    nx.set(0); ny.set(0);
    glowX.set(50); glowY.set(42);
    setHoveredZone(null);
  }, [nx, ny, glowX, glowY]);

  const sheen = useMotionTemplate`radial-gradient(320px 220px at ${glowX}% ${glowY}%, rgba(255,255,255,0.07), transparent 65%)`;

  return (
    <div
      ref={zoneRef}
      className="relative mx-auto w-full max-w-[560px] select-none lg:mx-0 lg:max-w-none"
      onMouseMove={enableTilt ? onMouseMove : undefined}
      onMouseLeave={onMouseLeave}
    >
      {/* Ambient glow halo */}
      <motion.div
        className="pointer-events-none absolute -inset-8 rounded-[2.5rem] blur-3xl"
        animate={{
          opacity: hoveredZone === "left" ? 0.7 : hoveredZone === "right" ? 0.7 : 0.45,
          background: hoveredZone === "left"
            ? "radial-gradient(ellipse 80% 55% at 22% 50%, rgba(56,189,248,0.28), transparent 55%), radial-gradient(ellipse 80% 55% at 78% 50%, rgba(0,230,118,0.12), transparent 55%)"
            : hoveredZone === "right"
            ? "radial-gradient(ellipse 80% 55% at 22% 50%, rgba(56,189,248,0.12), transparent 55%), radial-gradient(ellipse 80% 55% at 78% 50%, rgba(0,230,118,0.28), transparent 55%)"
            : "radial-gradient(ellipse 80% 55% at 22% 50%, rgba(56,189,248,0.18), transparent 55%), radial-gradient(ellipse 80% 55% at 78% 50%, rgba(0,230,118,0.2), transparent 55%)",
        }}
        transition={{ duration: 0.5 }}
        aria-hidden
      />

      <motion.div
        className="relative overflow-hidden rounded-2xl border border-white/[0.1] bg-[#040406] shadow-[0_32px_80px_-24px_rgba(0,0,0,0.92),inset_0_1px_0_rgba(255,255,255,0.07)] motion-reduce:transform-none"
        style={{
          rotateX: enableTilt ? rotateX : 0,
          rotateY: enableTilt ? rotateY : 0,
          transformPerspective: 1200,
          transformStyle: "preserve-3d",
        }}
        aria-label="SwiftTrade system architecture"
      >
        {/* EU watermark — makes “EU-only” obvious at first sight */}
        <div className="pointer-events-none absolute inset-0 z-0">
          <div className="absolute -right-8 top-12 opacity-[0.10] blur-[0.2px] sm:opacity-[0.12]">
            <EUMapIcon
              className="h-[260px] w-[260px] text-emerald-400/80 sm:h-[320px] sm:w-[320px]"
              title="EU market focus"
            />
          </div>
          <div
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse 70% 60% at 75% 40%, rgba(0,230,118,0.12), transparent 62%), radial-gradient(ellipse 80% 70% at 30% 55%, rgba(56,189,248,0.08), transparent 60%)",
            }}
            aria-hidden
          />
        </div>

        {/* Cursor sheen */}
        {enableTilt && (
          <motion.div
            className="pointer-events-none absolute inset-0 z-[1] opacity-60"
            style={{ background: sheen }}
            aria-hidden
          />
        )}

        {/* ── Header ── */}
        <motion.div
          className="relative z-10 flex items-center justify-between border-b border-white/[0.07] bg-white/[0.02] px-5 py-3.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
        >
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/50 motion-reduce:animate-none" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(0,230,118,0.9)]" />
            </div>
            <span className="text-[0.64rem] font-bold uppercase tracking-[0.22em] text-slate-400">
              How it works
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, repeatDelay: 4, ease: "easeInOut" }}
            >
              <Zap className="h-3 w-3 text-emerald-400" strokeWidth={2.5} />
            </motion.div>
            <span className="text-[0.6rem] font-bold text-emerald-300">Live signals</span>
          </div>
        </motion.div>

        {/* ── Two-zone body ── */}
        <div className="relative grid grid-cols-2">

          {/* LEFT — Cloud Portal */}
          <Zone
            side="left"
            icon={Cloud}
            title="Cloud Portal"
            subtitle="swifttrade.app"
            tone="sky"
            footerDot="bg-rose-500/55"
            footerText="No API keys stored here"
            hoveredZone={hoveredZone}
            onEnter={() => setHoveredZone("left")}
            onLeave={() => setHoveredZone(null)}
          >
            {/* Vertical flow dots */}
            {!reduce && <ZoneFlowDot delay={0.8} tone="sky" top={36} />}
            {!reduce && <ZoneFlowDot delay={3.5} tone="sky" top={36} />}

            <FeatureRow id="portal" icon={LayoutDashboard} label="Account & billing" tone="sky" delay={0.14} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
            <FeatureRow id="signals" icon={Zap} label="Signal generation" tone="sky" delay={0.20} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
            <FeatureRow id="license" icon={KeyRound} label="License management" tone="sky" delay={0.26} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
          </Zone>

          {/* RIGHT — Local Machine */}
          <Zone
            side="right"
            icon={Monitor}
            title="Your Machine"
            subtitle="Windows desktop"
            tone="emerald"
            footerDot="bg-emerald-400/60"
            footerText="Keys never leave this machine"
            hoveredZone={hoveredZone}
            onEnter={() => setHoveredZone("right")}
            onLeave={() => setHoveredZone(null)}
          >
            {/* Vertical flow dots */}
            {!reduce && <ZoneFlowDot delay={2.1} tone="emerald" top={36} />}
            {!reduce && <ZoneFlowDot delay={5.4} tone="emerald" top={36} />}

            <FeatureRow id="desktop" icon={Monitor} label="Desktop executor" tone="emerald" delay={0.14} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
            <FeatureRow id="apikey" icon={Lock} label="API key (local only)" tone="emerald" delay={0.20} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
            <FeatureRow id="t212" icon={TrendingUp} label="Trading212 orders" tone="neutral" delay={0.26} hoveredId={hoveredRow} onHoverStart={setHoveredRow} onHoverEnd={() => setHoveredRow(null)} />
          </Zone>

          {/* ── Security boundary ── */}
          <div className="pointer-events-none absolute inset-y-0 left-1/2 z-10 flex -translate-x-1/2 flex-col items-center justify-center">
            {/* Vertical amber line */}
            <motion.div
              className="absolute inset-y-0 w-px"
              style={{
                background:
                  "linear-gradient(to bottom, transparent 0%, rgba(251,191,36,0.18) 14%, rgba(251,191,36,0.5) 36%, rgba(251,191,36,0.5) 64%, rgba(251,191,36,0.18) 86%, transparent 100%)",
              }}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 0.65, delay: 0.28, ease: "easeOut" }}
            />

            {/* Shimmer sweep on the line */}
            {!reduce && (
              <motion.div
                className="absolute w-px"
                style={{ height: "40%", background: "linear-gradient(to bottom, transparent, rgba(251,191,36,0.8), transparent)" }}
                animate={{ top: ["10%", "50%", "90%", "50%", "10%"] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                aria-hidden
              />
            )}

            {/* Lock badge */}
            <motion.div
              className="relative flex h-9 w-9 items-center justify-center rounded-full border border-amber-400/45 bg-[#060507]"
              style={{ boxShadow: "0 0 28px -4px rgba(251,191,36,0.75)" }}
              initial={{ opacity: 0, scale: 0.4 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35, delay: 0.58, ease: EASE_SNAPPY }}
              whileHover={{ scale: 1.15 }}
            >
              <motion.div
                animate={{ rotate: [0, -8, 8, 0] }}
                transition={{ duration: 4, repeat: Infinity, repeatDelay: 3, ease: "easeInOut" }}
              >
                <Lock className="h-4 w-4 text-amber-300" strokeWidth={1.75} />
              </motion.div>

              {/* Pulse ring 1 */}
              {!reduce && (
                <motion.div
                  className="absolute inset-0 rounded-full border border-amber-400/25"
                  animate={{ scale: [1, 1.9, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
                  aria-hidden
                />
              )}
              {/* Pulse ring 2 — offset */}
              {!reduce && (
                <motion.div
                  className="absolute inset-0 rounded-full border border-amber-400/15"
                  animate={{ scale: [1, 2.5, 1], opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
                  aria-hidden
                />
              )}
            </motion.div>

            {/* Signal particles crossing */}
            <SignalParticle delay={1.4} duration={1.1} repeatDelay={5.2} size={5} />
            <SignalParticle delay={3.8} duration={0.95} repeatDelay={5.2} size={4} color="#34d399" />
            <SignalParticle delay={6.5} duration={1.3} repeatDelay={5.2} size={6} />
          </div>
        </div>

        {/* ── Footer ── */}
        <motion.div
          className="relative z-10 border-t border-white/[0.06] bg-white/[0.015] px-5 py-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          <div className="flex items-center justify-center gap-4 text-[0.62rem] text-slate-600">
            <motion.span
              className="flex items-center gap-1.5"
              animate={{ opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400/60" />
              Signals cross the boundary
            </motion.span>
            <span className="text-slate-800">·</span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400/60" />
              API keys never do
            </span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
