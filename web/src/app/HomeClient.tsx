"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  Filter,
  GitBranch,
  Lock,
  ShieldCheck,
  TrendingUp,
  Zap,
} from "lucide-react";

import { BacktestChart } from "@/components/BacktestChart";
import { BacktestSummary } from "@/components/BacktestSummary";
import { HeroPipelineVisual } from "@/components/home/HeroPipelineVisual";
import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { StatsTicker } from "@/components/home/StatsTicker";
import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";

export type HomeCtaMode =
  | { kind: "visitor" }
  | { kind: "member"; hasPro: boolean; checkoutEnabled: boolean };

const HOW_IT_WORKS = [
  {
    n: "01",
    title: "Create your portal account",
    desc: "Sign up to access the portal, manage your subscription, and receive your desktop license key.",
    tag: "Free · 2 min",
  },
  {
    n: "02",
    title: "Install the Windows desktop executor",
    desc: "Download the app and activate with your license key. Your Trading212 API key stays on your PC — never transmitted.",
    tag: "Windows · Local",
  },
  {
    n: "03",
    title: "Receive signals & execute locally",
    desc: "Signals publish via Supabase Realtime; the desktop app subscribes and places orders directly from your machine.",
    tag: "< 200ms",
  },
];

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "API keys never leave your PC",
    desc: "The desktop executor runs 100% locally. Your brokerage credentials are stored on your machine only, never transmitted to our servers.",
    tone: "emerald" as const,
    tag: "Security",
  },
  {
    icon: Zap,
    title: "Realtime signal delivery",
    desc: "Signals are pushed via Supabase Realtime. The executor subscribes and reacts immediately, without routing broker credentials through the web.",
    tone: "emerald" as const,
    tag: "< 200ms latency",
  },
  {
    icon: GitBranch,
    title: "Portal + executor split",
    desc: "The portal handles account, subscription & licensing. The desktop app is the only component that talks to Trading212.",
    tone: "sky" as const,
    tag: "Architecture",
  },
  {
    icon: Filter,
    title: "Strategy + risk controls",
    desc: "Long-only approach with protective logic enforced by the executor. Capital preservation is treated as a first-class goal.",
    tone: "gold" as const,
    tag: "Risk mgmt",
  },
];

const PERFORMANCE_METRICS = [
  { label: "CAGR", value: "+32.5%", sub: "5-yr sim · 12-mo OOS", positive: true },
  { label: "Win Rate", value: "58.3%", sub: "312 trades (OOS)", positive: true },
  { label: "Sharpe Ratio", value: "1.83", sub: "Risk-adjusted return", positive: true },
  { label: "Signal Latency", value: "< 200ms", sub: "Realtime push", positive: true },
];

const TRUST_PILLS = ["Keys stay local", "Supabase Realtime", "Windows executor", "EU-listed universe"];

const TONE_STYLES = {
  emerald: {
    icon: "bg-emerald-500/15 border-emerald-500/30 text-emerald-400",
    tag: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    hover: "hover:border-emerald-500/25 hover:shadow-[0_20px_40px_-24px_rgba(0,230,118,0.2)]",
  },
  sky: {
    icon: "bg-sky-500/15 border-sky-500/30 text-sky-400",
    tag: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    hover: "hover:border-sky-500/25 hover:shadow-[0_20px_40px_-24px_rgba(56,189,248,0.18)]",
  },
  gold: {
    icon: "bg-amber-500/15 border-amber-500/30 text-amber-400",
    tag: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    hover: "hover:border-amber-500/25 hover:shadow-[0_20px_40px_-24px_rgba(245,158,11,0.18)]",
  },
};

const HERO_METRICS = [
  { label: "CAGR", value: "+32.5%", positive: true },
  { label: "Win Rate", value: "58.3%", positive: true },
  { label: "Sharpe", value: "1.83", positive: true },
];

function HomeHeroCtas({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/login" className="gap-2">
          Create account <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/pricing" variant="secondary">
          View pricing
        </ButtonLink>
      </div>
    );
  }

  if (mode.hasPro) {
    return (
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/dashboard" className="gap-2">
          Open dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/download" variant="secondary">
          Download desktop app
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-3">
      {mode.checkoutEnabled ? (
        <form action="/api/stripe/checkout" method="post">
          <Button type="submit" className="gap-2">
            Upgrade to Pro <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      ) : (
        <ButtonLink href="/dashboard" className="gap-2">
          Go to dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
      )}
      <ButtonLink href="/pricing" variant="secondary">
        Compare plans
      </ButtonLink>
    </div>
  );
}

function HomeHeroBadge({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="live-dot relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
        </span>
        Integration ready
      </Badge>
    );
  }
  if (mode.hasPro) {
    return <Badge className="border-emerald-500/35 bg-emerald-500/15 text-emerald-200">Pro active</Badge>;
  }
  return <Badge className="border-emerald-500/35 bg-emerald-500/15 text-emerald-200">Signed in</Badge>;
}

function HomePricingCtas({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <div className="flex flex-wrap justify-center gap-4">
        <ButtonLink href="/pricing" className="gap-2">
          Compare plans <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/login" variant="secondary">
          Create free account
        </ButtonLink>
      </div>
    );
  }

  if (mode.hasPro) {
    return (
      <div className="flex flex-wrap justify-center gap-4">
        <ButtonLink href="/dashboard" className="gap-2">
          Dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/download" variant="secondary">
          Download app
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap justify-center gap-4">
      {mode.checkoutEnabled ? (
        <form action="/api/stripe/checkout" method="post">
          <Button type="submit" className="gap-2">
            Upgrade to Pro <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      ) : (
        <ButtonLink href="/dashboard" className="gap-2">
          Go to dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
      )}
      <ButtonLink href="/pricing" variant="secondary">
        View pricing
      </ButtonLink>
    </div>
  );
}

export function HomeClient({ ctaMode }: { ctaMode: HomeCtaMode }) {
  return (
    <div className="relative overflow-x-hidden">
      {/* ── Hero ── */}
      <section className="relative pb-20 pt-16 lg:pb-24 lg:pt-24">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[560px] w-[min(100%,1000px)] -translate-x-1/2 rounded-full opacity-75 blur-3xl"
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(0,230,118,0.13) 0%, rgba(16,185,129,0.05) 40%, transparent 70%)",
          }}
          aria-hidden
        />

        <Container>
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-xl space-y-7"
            >
              <HomeHeroBadge mode={ctaMode} />

              <div className="space-y-5">
                <h1 className="text-balance text-4xl font-semibold leading-[1.07] tracking-tight sm:text-5xl lg:text-[3.5rem]">
                  <span className="text-gradient-hero">Automated investing on</span>{" "}
                  <span className="text-gradient-shimmer">Trading212</span>
                  <br className="hidden lg:block" />
                  <span className="text-gradient-hero"> — without a pro setup</span>
                </h1>

                <p className="max-w-md text-base leading-relaxed text-slate-400 sm:text-[1.05rem]">
                  Signals and subscription live in the portal. Execution stays on your PC — your Trading212 API key
                  never touches this website.
                </p>
              </div>

              <HomeHeroCtas mode={ctaMode} />

              {/* Mini performance metrics row */}
              <div className="flex flex-wrap items-center gap-2">
                {HERO_METRICS.map((m) => (
                  <div
                    key={m.label}
                    className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5"
                  >
                    <span className="text-xs text-slate-500">{m.label}</span>
                    <span className={`font-mono text-xs font-semibold ${m.positive ? "text-emerald-400" : "text-rose-400"}`}>
                      {m.value}
                    </span>
                  </div>
                ))}
                <div className="flex items-center gap-1.5 rounded-full border border-slate-800/80 bg-white/[0.02] px-3 py-1.5">
                  <span className="text-xs text-slate-600">12-mo OOS · 5-yr sim</span>
                </div>
              </div>

              <ul className="flex flex-wrap gap-2">
                {TRUST_PILLS.map((pill) => (
                  <li
                    key={pill}
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500/70" />
                    {pill}
                  </li>
                ))}
              </ul>

              <p className="text-xs leading-relaxed text-slate-700">
                Not financial advice. Trading involves risk; past results do not guarantee future returns. Tax depends on
                your country.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
              className="relative flex justify-center lg:justify-end"
            >
              <HeroPipelineVisual />
            </motion.div>
          </div>
        </Container>
      </section>

      <StatsTicker />

      {/* ── How it works ── */}
      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-20 lg:py-24">
          <Container>
            <div className="glass-panel-strong relative overflow-hidden rounded-[1.75rem] p-8 sm:p-10 lg:p-12">
              <div className="pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full bg-emerald-500/8 blur-3xl" />
              <div className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-sky-500/8 blur-3xl" />

              <div className="relative mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div className="max-w-lg">
                  <SectionLabel>How it works</SectionLabel>
                  <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                    Three steps to automated investing
                  </h2>
                </div>
                <p className="max-w-sm text-sm leading-relaxed text-slate-400 md:text-right">
                  The portal manages your account. The desktop app is the only component that stores your
                  Trading212 API key.
                </p>
              </div>

              <div className="relative grid gap-4 md:grid-cols-3">
                {/* Subtle connecting line on desktop */}
                <div
                  className="pointer-events-none absolute inset-x-[calc(33%/2)] top-[2.6rem] hidden h-px md:block"
                  style={{
                    background:
                      "linear-gradient(90deg, transparent 0%, rgba(0,230,118,0.18) 25%, rgba(0,230,118,0.18) 75%, transparent 100%)",
                  }}
                  aria-hidden
                />

                {HOW_IT_WORKS.map((step) => (
                  <div
                    key={step.n}
                    className="group relative rounded-2xl border border-white/[0.07] bg-[#060608]/80 p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-emerald-500/25 hover:bg-[#08080c] hover:shadow-[0_16px_40px_-20px_rgba(0,230,118,0.18)] motion-reduce:hover:transform-none"
                  >
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-2xl bg-gradient-to-r from-transparent via-white/8 to-transparent transition-all duration-300 group-hover:via-emerald-500/20" />

                    <div className="mb-5 flex items-center gap-3">
                      <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_18px_-4px_rgba(0,230,118,0.28)]">
                        <span className="font-mono text-xs font-bold text-emerald-300">{step.n}</span>
                      </div>
                      <span className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[0.7rem] text-slate-500">
                        {step.tag}
                      </span>
                    </div>

                    <h3 className="mb-2 text-base font-semibold leading-snug text-slate-50">{step.title}</h3>
                    <p className="text-sm leading-relaxed text-slate-400">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Performance metrics ── */}
      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-16 lg:py-20">
          <Container>
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <SectionLabel>Performance metrics</SectionLabel>
              <span className="text-xs text-slate-700">5-year simulation · 12-month OOS · illustrative only</span>
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
              {PERFORMANCE_METRICS.map((m) => (
                <div
                  key={m.label}
                  className="glass-panel group relative overflow-hidden rounded-2xl p-6 text-center transition-all duration-300 hover:border-emerald-500/20 hover:shadow-[0_16px_40px_-20px_rgba(0,230,118,0.15)]"
                >
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-500/18 to-transparent" />
                  <p
                    className={`mb-1 font-mono text-2xl font-semibold tabular-nums sm:text-3xl ${
                      m.positive ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {m.value}
                  </p>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{m.label}</p>
                  <p className="mt-1.5 text-[0.65rem] text-slate-600">{m.sub}</p>
                </div>
              ))}
            </div>

            <p className="mt-4 text-center text-xs text-slate-700">
              Backtested results on historical data. Not a guarantee of future performance. Not financial advice.
            </p>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Features ── */}
      <RevealOnScroll>
        <section className="py-20 lg:py-28">
          <Container>
            <div className="mb-12 max-w-2xl">
              <SectionLabel>Platform capabilities</SectionLabel>
              <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Built for security-conscious traders
              </h2>
            </div>

            <motion.div
              className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.15 }}
              variants={{
                hidden: {},
                show: { transition: { staggerChildren: 0.07, delayChildren: 0.02 } },
              }}
            >
              {FEATURES.map((f) => {
                const tone = TONE_STYLES[f.tone];
                return (
                  <motion.div
                    key={f.title}
                    variants={{
                      hidden: { opacity: 0, y: 16, filter: "blur(6px)" },
                      show: { opacity: 1, y: 0, filter: "blur(0px)" },
                    }}
                    transition={{ duration: 0.45, ease: "easeOut" }}
                    className={`group relative h-full rounded-2xl border border-white/[0.08] bg-[#060608]/80 p-6 transition-all duration-300 hover:-translate-y-1 ${tone.hover} motion-reduce:hover:transform-none`}
                  >
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-2xl bg-gradient-to-r from-transparent via-white/8 to-transparent" />

                    <div
                      className={`mb-4 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] ${tone.icon}`}
                    >
                      <f.icon className="h-5 w-5" />
                    </div>

                    <div className={`mb-4 inline-block rounded-full border px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${tone.tag}`}>
                      {f.tag}
                    </div>

                    <h3 className="mb-2 font-semibold leading-snug text-slate-50">{f.title}</h3>
                    <p className="text-sm leading-relaxed text-slate-400">{f.desc}</p>
                  </motion.div>
                );
              })}
            </motion.div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Security architecture ── */}
      <RevealOnScroll>
        <section className="pb-8 pt-4 lg:pb-12">
          <Container>
            <div className="glass-panel-strong relative grid items-center gap-10 overflow-hidden rounded-[1.75rem] p-8 md:grid-cols-2 md:p-12 lg:p-14">
              <div className="pointer-events-none absolute -right-32 -top-32 h-80 w-80 rounded-full bg-emerald-500/10 blur-3xl" />
              <div className="pointer-events-none absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-sky-500/8 blur-3xl" />

              <div className="relative">
                <SectionLabel>Security architecture</SectionLabel>
                <h2 className="mb-4 text-balance text-3xl font-semibold tracking-tight text-white">
                  Your keys stay on your machine. Always.
                </h2>
                <p className="mb-8 text-sm leading-relaxed text-slate-400 sm:text-base">
                  SwiftTrade is split into two layers: a web portal for account and subscription management, and a local
                  Windows executor that holds your broker API keys. The portal{" "}
                  <em className="not-italic text-slate-200">never</em> sees your credentials.
                </p>
                <ButtonLink href="/product" variant="secondary" className="gap-2">
                  Read the product overview <ArrowRight className="h-4 w-4" />
                </ButtonLink>
              </div>

              <div className="relative space-y-3">
                {[
                  {
                    icon: Cpu,
                    label: "Web Portal",
                    sub: "Account · Subscription · Signals",
                    border: "border-sky-500/25",
                    bg: "bg-sky-500/[0.06]",
                    iconCls: "border-sky-500/25 bg-sky-500/10 text-sky-400",
                    dot: "bg-sky-400",
                  },
                  {
                    icon: Lock,
                    label: "Desktop App",
                    sub: "API Keys · Order Executor · Local",
                    border: "border-emerald-500/35",
                    bg: "bg-emerald-500/[0.08]",
                    iconCls: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
                    dot: "bg-emerald-400",
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className={`flex items-center gap-4 rounded-xl border ${row.border} ${row.bg} p-4 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] transition-all duration-200 hover:brightness-110`}
                  >
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${row.iconCls}`}>
                      <row.icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-100">{row.label}</p>
                      <p className="text-xs text-slate-500">{row.sub}</p>
                    </div>
                    <span className={`h-2 w-2 shrink-0 rounded-full ${row.dot} opacity-70 shadow-[0_0_8px_currentColor]`} />
                  </div>
                ))}

                <div className="flex items-center justify-center gap-2 pt-1">
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                  <p className="text-center text-[0.65rem] text-slate-600">
                    One-way signal push · credentials never cross the boundary
                  </p>
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                </div>
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Strategy results ── */}
      <RevealOnScroll>
        <section className="py-8 pb-24 lg:pb-28">
          <Container>
            <GlowHoverCard className="overflow-hidden p-0">
              {/* Terminal chrome header */}
              <div className="flex items-center justify-between border-b border-white/[0.07] bg-white/[0.02] px-7 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <span className="h-3 w-3 rounded-full bg-rose-500/60" />
                    <span className="h-3 w-3 rounded-full bg-amber-500/60" />
                    <span className="h-3 w-3 rounded-full bg-emerald-500/60" />
                  </div>
                  <div>
                    <SectionLabel className="mb-0">Historical model output</SectionLabel>
                  </div>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-xs font-semibold text-emerald-300">Results (example)</span>
                </div>
              </div>

              <div className="p-7 md:p-10">
                <div className="mb-6">
                  <h2 className="text-2xl font-semibold tracking-tight text-white">Strategy results</h2>
                  <p className="mt-1.5 text-sm text-slate-500">Monthly view · equity indexed to 100 at start</p>
                </div>

                <motion.div
                  className="rounded-2xl border border-white/[0.07] bg-[#040406] p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.25 }}
                  transition={{ duration: 0.45, ease: "easeOut" }}
                >
                  <BacktestChart />
                  <BacktestSummary />
                </motion.div>

                <p className="mt-5 text-xs leading-relaxed text-slate-700">
                  Results shown are illustrative and not a guarantee of future performance. Your actual results will vary.
                  This is not financial advice.
                </p>
              </div>
            </GlowHoverCard>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── CTA ── */}
      <RevealOnScroll>
        <section className="pb-28 pt-4 lg:pb-36">
          <Container>
            <div className="relative rounded-[1.75rem] bg-gradient-to-br from-emerald-400/45 via-emerald-600/28 to-teal-500/38 p-px shadow-[0_0_80px_-20px_rgba(0,230,118,0.3)]">
              <div className="relative overflow-hidden rounded-[calc(1.75rem-1px)] bg-[#040406] px-8 py-14 text-center md:px-16 md:py-20">
                {/* Background grid */}
                <div
                  className="pointer-events-none absolute inset-0 opacity-[0.04]"
                  style={{
                    backgroundImage:
                      "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
                    backgroundSize: "48px 48px",
                  }}
                  aria-hidden
                />

                <div className="pointer-events-none absolute -left-24 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full bg-emerald-500/15 blur-3xl" />
                <div className="pointer-events-none absolute -right-24 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full bg-teal-500/10 blur-3xl" />

                <div className="relative">
                  <Badge className="mb-6 border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                    Simple, transparent pricing
                  </Badge>
                  <h2 className="text-balance mb-4 text-3xl font-semibold tracking-tight text-white md:text-5xl">
                    Start free. Go live when ready.
                  </h2>
                  <p className="mx-auto mb-10 max-w-lg text-base leading-relaxed text-slate-400">
                    Explore the portal on the free plan. Upgrade to Pro for the live signal feed, a desktop license, and
                    executor downloads.
                  </p>
                  <HomePricingCtas mode={ctaMode} />
                </div>
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>
    </div>
  );
}
