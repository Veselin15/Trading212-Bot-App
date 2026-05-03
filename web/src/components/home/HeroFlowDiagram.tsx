"use client";

import { motion, useReducedMotion } from "framer-motion";

const W = 640;
const H = 420;
const CX = W / 2; // 320

const BADGE_H = 44;
const SOURCES = [
  { cx: 170, w: 244, label: "◆ TradingView alerts (strategy signals)" },
  { cx: 474, w: 268, label: "◻ Portal (login · billing · license)" },
] as const;

const FEED_TOP = 126;
const FEED_H = 64;
const FEED_W = 330;
const FEED_BOT = FEED_TOP + FEED_H; // 190
const FEED_CY = FEED_TOP + FEED_H / 2; // 158

const EXEC_TOP = 242;
const EXEC_H = 72;
const EXEC_W = 362;
const EXEC_BOT = EXEC_TOP + EXEC_H; // 314
const EXEC_CY = EXEC_TOP + EXEC_H / 2; // 278

const T212_Y = 366;

function srcToFeedPath(src: (typeof SOURCES)[number]) {
  const sy = BADGE_H;
  const midY = (sy + FEED_TOP) / 2;
  return `M ${src.cx},${sy} C ${src.cx},${midY} ${CX},${midY} ${CX},${FEED_TOP}`;
}

const FEED_TO_EXEC_PATH = `M ${CX},${FEED_BOT} L ${CX},${EXEC_TOP}`;
const EXEC_TO_T212_PATH = `M ${CX},${EXEC_BOT} L ${CX},${T212_Y}`;

export function HeroFlowDiagram() {
  const reduceMotion = useReducedMotion();

  return (
    <div className="relative w-full" style={{ maxWidth: 660 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" overflow="visible" xmlns="http://www.w3.org/2000/svg">
        <defs>
          {/* Badge fill */}
          <linearGradient id="hfd-badgeFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(15,23,42,0.95)" />
            <stop offset="100%" stopColor="rgba(2,6,23,0.88)" />
          </linearGradient>

          {/* Pill fills — subtle tinted glass */}
          <linearGradient id="hfd-feedFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(8,26,54,0.97)" />
            <stop offset="45%" stopColor="rgba(3,10,32,0.86)" />
            <stop offset="100%" stopColor="rgba(2,6,23,0.98)" />
          </linearGradient>
          <linearGradient id="hfd-execFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(6,28,42,0.97)" />
            <stop offset="45%" stopColor="rgba(4,14,28,0.86)" />
            <stop offset="100%" stopColor="rgba(2,6,23,0.98)" />
          </linearGradient>

          {/* Pill borders — symmetric, brightness peaks at center */}
          <linearGradient id="hfd-feedStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(16,185,129,0.22)" />
            <stop offset="28%" stopColor="rgba(0,230,118,0.78)" />
            <stop offset="50%" stopColor="rgba(34,211,238,0.98)" />
            <stop offset="72%" stopColor="rgba(0,230,118,0.78)" />
            <stop offset="100%" stopColor="rgba(16,185,129,0.22)" />
          </linearGradient>
          <linearGradient id="hfd-execStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(0,230,118,0.22)" />
            <stop offset="28%" stopColor="rgba(16,185,129,0.78)" />
            <stop offset="50%" stopColor="rgba(0,230,118,1)" />
            <stop offset="72%" stopColor="rgba(16,185,129,0.78)" />
            <stop offset="100%" stopColor="rgba(0,230,118,0.22)" />
          </linearGradient>

          {/* Outer glow halos */}
          <radialGradient id="hfd-feedGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(16,185,129,0.26)" />
            <stop offset="52%" stopColor="rgba(0,230,118,0.11)" />
            <stop offset="100%" stopColor="rgba(16,185,129,0)" />
          </radialGradient>
          <radialGradient id="hfd-execGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(0,230,118,0.24)" />
            <stop offset="52%" stopColor="rgba(16,185,129,0.09)" />
            <stop offset="100%" stopColor="rgba(0,230,118,0)" />
          </radialGradient>

          {/* Animated flow pulses on lines */}
          <linearGradient id="hfd-skyPulse" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(16,185,129,0)" />
            <stop offset="38%" stopColor="rgba(0,230,118,0.9)" />
            <stop offset="60%" stopColor="rgba(34,211,238,0.88)" />
            <stop offset="100%" stopColor="rgba(16,185,129,0)" />
          </linearGradient>
          <linearGradient id="hfd-emeraldPulse" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(16,185,129,0)" />
            <stop offset="50%" stopColor="rgba(0,230,118,0.92)" />
            <stop offset="100%" stopColor="rgba(16,185,129,0)" />
          </linearGradient>

          {/* Drop shadow for pills */}
          <filter id="hfd-pillShadow" x="-28%" y="-45%" width="156%" height="230%">
            <feDropShadow dx="0" dy="10" stdDeviation="14" floodColor="rgba(0,0,0,0.72)" floodOpacity="1" />
          </filter>

          {/* Soft glow for animated lines */}
          <filter id="hfd-lineGlow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="2.6" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Title text glow */}
          <filter id="hfd-titleGlow" x="-18%" y="-55%" width="136%" height="210%">
            <feGaussianBlur stdDeviation="1.6" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <marker id="hfd-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(148,163,184,0.52)" />
          </marker>
        </defs>

        {/* ── Ambient background hazes ── */}
        <ellipse cx={CX}       cy={190} rx={290} ry={170} fill="rgba(2,6,23,0.22)" />
        <ellipse cx={CX - 90} cy={120} rx={230} ry={145} fill="rgba(16,185,129,0.06)" />
        <ellipse cx={CX + 70} cy={268} rx={240} ry={158} fill="rgba(0,230,118,0.05)" />

        {/* ── Source badges ── */}
        {SOURCES.map((src, i) => (
          <motion.g
            key={src.label}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.15, duration: 0.55, ease: "easeOut" }}
          >
            {/* body */}
            <rect
              x={src.cx - src.w / 2}
              y={0}
              width={src.w}
              height={BADGE_H}
              rx={BADGE_H / 2}
              fill="url(#hfd-badgeFill)"
              stroke="rgba(148,163,184,0.26)"
              strokeWidth={1.2}
            />
            {/* inner inset ring */}
            <rect
              x={src.cx - src.w / 2 + 1.5}
              y={1.5}
              width={src.w - 3}
              height={BADGE_H - 3}
              rx={BADGE_H / 2 - 1.5}
              fill="transparent"
              stroke="rgba(255,255,255,0.07)"
              strokeWidth={1}
            />
            {/* top-edge glass shine */}
            <path
              d={`M ${src.cx - src.w / 2 + 22} 5 Q ${src.cx} -3 ${src.cx + src.w / 2 - 22} 5`}
              fill="none"
              stroke="rgba(255,255,255,0.2)"
              strokeWidth={1.2}
              strokeLinecap="round"
            />
            <text
              x={src.cx}
              y={BADGE_H / 2 + 5}
              textAnchor="middle"
              fill="rgba(203,213,225,0.92)"
              fontSize="11.5"
              fontFamily="system-ui, sans-serif"
            >
              {src.label}
            </text>
          </motion.g>
        ))}

        {/* ── Bezier connectors: badges → FEED ── */}
        {SOURCES.map((src, i) => (
          <g key={`conn-${i}`}>
            {/* static base */}
            <motion.path
              d={srcToFeedPath(src)}
              fill="none"
              stroke="rgba(148,163,184,0.17)"
              strokeWidth={1.5}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.38 + i * 0.1, duration: 1.1, ease: "easeOut" }}
            />
            {/* animated flow */}
            <motion.path
              d={srcToFeedPath(src)}
              fill="none"
              stroke="url(#hfd-skyPulse)"
              strokeWidth={2.6}
              strokeLinecap="round"
              filter="url(#hfd-lineGlow)"
              strokeDasharray="14 36"
              initial={{ strokeDashoffset: 0 }}
              animate={reduceMotion ? { opacity: 0.28 } : { strokeDashoffset: [0, -150] }}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { duration: 2.5 + i * 0.3, repeat: Number.POSITIVE_INFINITY, ease: "linear", delay: 0.9 + i * 0.22 }
              }
            />
          </g>
        ))}

        {/* ── FEED → EXEC connector ── */}
        <g>
          <motion.path
            d={FEED_TO_EXEC_PATH}
            fill="none"
            stroke="rgba(148,163,184,0.22)"
            strokeWidth={1.5}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: 0.82, duration: 0.55, ease: "easeOut" }}
            markerEnd="url(#hfd-arrow)"
          />
          <motion.path
            d={FEED_TO_EXEC_PATH}
            fill="none"
            stroke="url(#hfd-skyPulse)"
            strokeWidth={2.6}
            strokeLinecap="round"
            filter="url(#hfd-lineGlow)"
            strokeDasharray="12 32"
            initial={{ strokeDashoffset: 0 }}
            animate={reduceMotion ? { opacity: 0.28 } : { strokeDashoffset: [0, -100] }}
            transition={
              reduceMotion ? { duration: 0 } : { duration: 2.1, repeat: Number.POSITIVE_INFINITY, ease: "linear", delay: 1.1 }
            }
          />
        </g>

        {/* ── EXEC → T212 connector ── */}
        <g>
          <motion.path
            d={EXEC_TO_T212_PATH}
            fill="none"
            stroke="rgba(148,163,184,0.22)"
            strokeWidth={1.5}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: 1.05, duration: 0.55, ease: "easeOut" }}
            markerEnd="url(#hfd-arrow)"
          />
          <motion.path
            d={EXEC_TO_T212_PATH}
            fill="none"
            stroke="url(#hfd-emeraldPulse)"
            strokeWidth={2.6}
            strokeLinecap="round"
            filter="url(#hfd-lineGlow)"
            strokeDasharray="12 32"
            initial={{ strokeDashoffset: 0 }}
            animate={reduceMotion ? { opacity: 0.28 } : { strokeDashoffset: [0, -100] }}
            transition={
              reduceMotion ? { duration: 0 } : { duration: 1.9, repeat: Number.POSITIVE_INFINITY, ease: "linear", delay: 1.3 }
            }
          />
        </g>

        {/* ── CLOUD tag ── */}
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 0.45 }}>
          <rect
            x={CX - 42}
            y={FEED_TOP - 29}
            width={84}
            height={21}
            rx={10.5}
            fill="rgba(16,185,129,0.11)"
            stroke="rgba(16,185,129,0.42)"
            strokeWidth={1}
          />
          <text
            x={CX}
            y={FEED_TOP - 14}
            textAnchor="middle"
            fill="rgba(125,211,252,1)"
            fontSize="10.5"
            fontFamily="system-ui, sans-serif"
            letterSpacing="1.5"
            fontWeight="600"
          >
            CLOUD
          </text>
        </motion.g>

        {/* ── FEED pill ── */}
        <motion.g
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ transformOrigin: `${CX}px ${FEED_CY}px` }}
          transition={{ delay: 0.55, duration: 0.55, ease: "easeOut" }}
        >
          {/* outer ambient glow halo */}
          <ellipse cx={CX} cy={FEED_CY} rx={FEED_W / 2 + 60} ry={FEED_H / 2 + 42} fill="url(#hfd-feedGlow)" />
          {/* pill with drop shadow */}
          <rect
            x={CX - FEED_W / 2}
            y={FEED_TOP}
            width={FEED_W}
            height={FEED_H}
            rx={FEED_H / 2}
            fill="url(#hfd-feedFill)"
            stroke="url(#hfd-feedStroke)"
            strokeWidth={1.5}
            filter="url(#hfd-pillShadow)"
          />
          {/* inner inset ring */}
          <rect
            x={CX - FEED_W / 2 + 2}
            y={FEED_TOP + 2}
            width={FEED_W - 4}
            height={FEED_H - 4}
            rx={FEED_H / 2 - 2}
            fill="transparent"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
          />
          {/* top-edge glass shine arc */}
          <path
            d={`M ${CX - FEED_W / 2 + FEED_H / 2 - 4} ${FEED_TOP + 6} Q ${CX} ${FEED_TOP - 7} ${CX + FEED_W / 2 - FEED_H / 2 + 4} ${FEED_TOP + 6}`}
            fill="none"
            stroke="rgba(255,255,255,0.24)"
            strokeWidth={1.5}
            strokeLinecap="round"
          />
          {/* title */}
          <text
            x={CX}
            y={FEED_CY + 2}
            textAnchor="middle"
            fill="#7dd3fc"
            fontSize="13.5"
            fontFamily="system-ui, sans-serif"
            fontWeight="700"
            letterSpacing="0.9"
            filter="url(#hfd-titleGlow)"
          >
            SUPABASE REALTIME FEED
          </text>
          {/* subtitle */}
          <text
            x={CX}
            y={FEED_CY + 20}
            textAnchor="middle"
            fill="rgba(148,163,184,0.72)"
            fontSize="10.5"
            fontFamily="system-ui, sans-serif"
          >
            RLS gated · subscribers only · no broker keys
          </text>
        </motion.g>

        {/* ── LOCAL tag ── */}
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7, duration: 0.45 }}>
          <rect
            x={CX - 38}
            y={EXEC_TOP - 29}
            width={76}
            height={21}
            rx={10.5}
            fill="rgba(0,230,118,0.1)"
            stroke="rgba(0,230,118,0.42)"
            strokeWidth={1}
          />
          <text
            x={CX}
            y={EXEC_TOP - 14}
            textAnchor="middle"
            fill="rgba(165,243,252,1)"
            fontSize="10.5"
            fontFamily="system-ui, sans-serif"
            letterSpacing="1.5"
            fontWeight="600"
          >
            LOCAL
          </text>
        </motion.g>

        {/* ── EXEC pill ── */}
        <motion.g
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ transformOrigin: `${CX}px ${EXEC_CY}px` }}
          transition={{ delay: 0.75, duration: 0.55, ease: "easeOut" }}
        >
          {/* outer ambient glow halo */}
          <ellipse cx={CX} cy={EXEC_CY} rx={EXEC_W / 2 + 64} ry={EXEC_H / 2 + 46} fill="url(#hfd-execGlow)" />
          {/* pill with drop shadow */}
          <rect
            x={CX - EXEC_W / 2}
            y={EXEC_TOP}
            width={EXEC_W}
            height={EXEC_H}
            rx={EXEC_H / 2}
            fill="url(#hfd-execFill)"
            stroke="url(#hfd-execStroke)"
            strokeWidth={1.5}
            filter="url(#hfd-pillShadow)"
          />
          {/* inner inset ring */}
          <rect
            x={CX - EXEC_W / 2 + 2}
            y={EXEC_TOP + 2}
            width={EXEC_W - 4}
            height={EXEC_H - 4}
            rx={EXEC_H / 2 - 2}
            fill="transparent"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
          />
          {/* top-edge glass shine arc */}
          <path
            d={`M ${CX - EXEC_W / 2 + EXEC_H / 2 - 4} ${EXEC_TOP + 6} Q ${CX} ${EXEC_TOP - 7} ${CX + EXEC_W / 2 - EXEC_H / 2 + 4} ${EXEC_TOP + 6}`}
            fill="none"
            stroke="rgba(255,255,255,0.24)"
            strokeWidth={1.5}
            strokeLinecap="round"
          />
          {/* title */}
          <text
            x={CX}
            y={EXEC_CY + 2}
            textAnchor="middle"
            fill="#a7f3d0"
            fontSize="13.5"
            fontFamily="system-ui, sans-serif"
            fontWeight="700"
            letterSpacing="0.9"
            filter="url(#hfd-titleGlow)"
          >
            WINDOWS DESKTOP EXECUTOR
          </text>
          {/* subtitle */}
          <text
            x={CX}
            y={EXEC_CY + 21}
            textAnchor="middle"
            fill="rgba(148,163,184,0.72)"
            fontSize="10.5"
            fontFamily="system-ui, sans-serif"
          >
            stores Trading212 API key locally · places orders
          </text>
        </motion.g>

        {/* ── Trading212 brand ── */}
        <motion.g
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.55, ease: "easeOut" }}
        >
          <text
            x={CX}
            y={T212_Y + 32}
            textAnchor="middle"
            fill="white"
            fontSize="24"
            fontFamily="'Geist', system-ui, sans-serif"
            fontWeight="700"
            letterSpacing="3"
            opacity={0.96}
          >
            TR∧DING212
          </text>
          <text x={CX + 100} y={T212_Y + 18} fill="rgba(148,163,184,0.45)" fontSize="11" fontFamily="system-ui">
            ®
          </text>
        </motion.g>
      </svg>
    </div>
  );
}
