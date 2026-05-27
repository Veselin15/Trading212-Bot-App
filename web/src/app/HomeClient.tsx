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
    desc: "Sign up to access the portal, manage your subscription, and see your desktop license key.",
  },
  {
    n: "02",
    title: "Install the Windows desktop executor",
    desc: "Download the desktop app and activate it with your license key. Your Trading212 API key stays local on your PC.",
  },
  {
    n: "03",
    title: "Receive realtime signals and execute locally",
    desc: "Signals are published in Supabase; the desktop app subscribes in realtime and places orders directly from your device.",
  },
];

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "API keys never leave your PC",
    desc: "The desktop executor runs 100% locally. Your brokerage credentials are stored on your machine only, never transmitted to our servers.",
  },
  {
    icon: Zap,
    title: "Realtime signal delivery",
    desc: "Signals are pushed via Supabase Realtime. The executor subscribes and reacts immediately, without routing broker credentials through the web.",
  },
  {
    icon: GitBranch,
    title: "Portal + executor split",
    desc: "The portal handles account + subscription + licensing. The desktop app is the only component that talks to Trading212.",
  },
  {
    icon: Filter,
    title: "Strategy + risk controls",
    desc: "Long-only approach with protective logic enforced by the executor. Capital preservation is treated as a first-class goal.",
  },
];

const STATS_ROW = [
  { value: "Long-only", label: "Strategy" },
  { value: "EU-listed", label: "Universe" },
  { value: "Local keys", label: "Security model" },
  { value: "Realtime", label: "Signal delivery" },
];

const TRUST_PILLS = ["Keys stay local", "Supabase Realtime", "Windows executor", "EU-listed universe"];

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
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
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
      <section className="relative pb-20 pt-16 lg:pb-24 lg:pt-24">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[520px] w-[min(100%,900px)] -translate-x-1/2 rounded-full opacity-80 blur-3xl"
          style={{
            background:
              "radial-gradient(ellipse at center, rgba(0,230,118,0.14) 0%, rgba(16,185,129,0.06) 40%, transparent 70%)",
          }}
          aria-hidden
        />

        <Container>
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-xl space-y-8"
            >
              <HomeHeroBadge mode={ctaMode} />

              <div className="space-y-5">
                <h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-[3.35rem]">
                  <span className="text-gradient-hero">Automated investing on</span>{" "}
                  <span className="text-gradient-brand">Trading212</span>
                  <span className="text-gradient-hero"> — without a pro setup</span>
                </h1>

                <p className="max-w-md text-base leading-relaxed text-slate-400 sm:text-lg">
                  Signals and subscription live in the portal. Execution stays on your PC — your Trading212 API key
                  never touches this website.
                </p>
              </div>

              <HomeHeroCtas mode={ctaMode} />

              <ul className="flex flex-wrap gap-2">
                {TRUST_PILLS.map((pill) => (
                  <li
                    key={pill}
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500/80" />
                    {pill}
                  </li>
                ))}
              </ul>

              <p className="text-xs leading-relaxed text-slate-600">
                Not financial advice. Trading involves risk; past results do not guarantee future returns. Tax depends on
                your country — not tax advice.
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

      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-20 lg:py-24">
          <Container>
            <div className="glass-panel-strong relative overflow-hidden rounded-[1.75rem] p-8 sm:p-10 lg:p-12">
              <div className="pointer-events-none absolute -left-32 -top-32 h-80 w-80 rounded-full bg-emerald-500/10 blur-3xl" />
              <div className="pointer-events-none absolute -bottom-32 -right-32 h-80 w-80 rounded-full bg-teal-500/10 blur-3xl" />

              <div className="relative mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div className="max-w-lg">
                  <SectionLabel>How it works</SectionLabel>
                  <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                    Portal + executor, split by design
                  </h2>
                </div>
                <p className="max-w-md text-sm leading-relaxed text-slate-400 md:text-right">
                  The website manages your account and subscription. The desktop app is the only component that stores
                  your Trading212 API key and places orders.
                </p>
              </div>

              <div className="relative grid gap-4 md:grid-cols-3">
                {HOW_IT_WORKS.map((step) => (
                  <div
                    key={step.n}
                    className="group rounded-2xl border border-white/[0.08] bg-[#060608]/80 p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-emerald-500/25 hover:bg-[#08080c] hover:shadow-[0_20px_40px_-24px_rgba(0,230,118,0.2)] motion-reduce:hover:transform-none"
                  >
                    <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1">
                      <span className="font-mono text-xs font-medium text-emerald-300">{step.n}</span>
                      <span className="text-xs text-slate-400">Step</span>
                    </div>
                    <h3 className="text-base font-semibold text-slate-50">{step.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-16 lg:py-20">
          <Container>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
              {STATS_ROW.map((s) => (
                <div
                  key={s.label}
                  className="glass-panel rounded-2xl p-6 text-center transition-colors hover:border-emerald-500/20"
                >
                  <p className="mb-1 font-mono text-2xl font-semibold tabular-nums text-emerald-400 sm:text-3xl">
                    {s.value}
                  </p>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{s.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-center text-xs text-slate-600">
              Backtested results on historical data. Not a guarantee of future performance.
            </p>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="py-20 lg:py-28">
          <Container>
            <div className="mb-14 max-w-2xl">
              <SectionLabel>Platform capabilities</SectionLabel>
              <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Built for security-conscious traders
              </h2>
            </div>

            <motion.div
              className="grid gap-5 md:grid-cols-2 lg:grid-cols-4"
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.2 }}
              variants={{
                hidden: {},
                show: { transition: { staggerChildren: 0.06, delayChildren: 0.02 } },
              }}
            >
              {FEATURES.map((f) => (
                <RevealOnScroll key={f.title}>
                  <GlowHoverCard className="h-full p-6">
                    <motion.div
                      variants={{
                        hidden: { opacity: 0, y: 12, filter: "blur(6px)" },
                        show: { opacity: 1, y: 0, filter: "blur(0px)" },
                      }}
                      transition={{ duration: 0.45, ease: "easeOut" }}
                      className="flex h-full flex-col gap-4"
                    >
                      <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-emerald-500/25 bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)]">
                        <f.icon className="h-5 w-5 text-emerald-400" />
                      </div>
                      <div>
                        <h3 className="mb-2 font-semibold leading-snug text-slate-50">{f.title}</h3>
                        <p className="text-sm leading-relaxed text-slate-400">{f.desc}</p>
                      </div>
                    </motion.div>
                  </GlowHoverCard>
                </RevealOnScroll>
              ))}
            </motion.div>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-8 pt-4 lg:pb-12">
          <Container>
            <div className="glass-panel-strong relative grid items-center gap-10 overflow-hidden rounded-[1.75rem] p-8 md:grid-cols-2 md:p-12 lg:p-14">
              <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />
              <div>
                <SectionLabel>Security architecture</SectionLabel>
                <h2 className="mb-4 text-balance text-3xl font-semibold tracking-tight text-white">
                  Your keys stay on your machine. Always.
                </h2>
                <p className="mb-8 text-sm leading-relaxed text-slate-400 sm:text-base">
                  SwiftTrade is split into two layers: a web portal for account and subscription management, and a local
                  Windows executor that holds your broker API keys. The portal <em className="text-slate-300">never</em>{" "}
                  sees your credentials.
                </p>
                <ButtonLink href="/product" variant="secondary" className="gap-2">
                  Read the product overview <ArrowRight className="h-4 w-4" />
                </ButtonLink>
              </div>

              <div className="space-y-3">
                {[
                  {
                    icon: Cpu,
                    label: "Web Portal",
                    sub: "Account · Subscription · Signals",
                    border: "border-white/[0.08]",
                    bg: "bg-white/[0.03]",
                  },
                  {
                    icon: Lock,
                    label: "Desktop App",
                    sub: "API Keys · Order Executor · Local",
                    border: "border-emerald-500/35",
                    bg: "bg-emerald-500/[0.08]",
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className={`flex items-center gap-4 rounded-xl border ${row.border} ${row.bg} p-4 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]`}
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-emerald-500/20 bg-emerald-500/10">
                      <row.icon className="h-5 w-5 flex-shrink-0 text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-100">{row.label}</p>
                      <p className="text-xs text-slate-500">{row.sub}</p>
                    </div>
                  </div>
                ))}
                <p className="pt-1 text-center text-xs text-slate-600">
                  One-way signal push · credentials never cross the boundary
                </p>
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="py-8 pb-24 lg:pb-28">
          <Container>
            <GlowHoverCard className="p-8 md:p-12">
              <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <SectionLabel>Historical model output</SectionLabel>
                  <h2 className="text-3xl font-semibold tracking-tight text-white">Strategy results</h2>
                  <p className="mt-2 text-sm text-slate-500">Monthly view · equity indexed to 100 at start</p>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-xs font-medium text-emerald-300">Results (example)</span>
                </div>
              </div>

              <motion.div
                className="rounded-2xl border border-white/[0.08] bg-[#060608] p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]"
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.45, ease: "easeOut" }}
              >
                <BacktestChart />
                <BacktestSummary />
              </motion.div>

              <p className="mt-5 text-xs leading-relaxed text-slate-600">
                Results shown are illustrative and not a guarantee of future performance. Your actual results will vary.
                This is not financial advice.
              </p>
            </GlowHoverCard>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-28 pt-4 lg:pb-36">
          <Container>
            <div className="relative rounded-[1.75rem] bg-gradient-to-br from-emerald-400/50 via-emerald-600/30 to-teal-500/40 p-px shadow-[0_0_60px_-20px_rgba(0,230,118,0.35)]">
              <div className="relative overflow-hidden rounded-[calc(1.75rem-1px)] bg-[#060608] px-8 py-14 text-center md:px-16 md:py-20">
                <div className="pointer-events-none absolute -left-24 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full bg-emerald-500/15 blur-3xl" />
                <div className="pointer-events-none absolute -right-24 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full bg-teal-500/10 blur-3xl" />

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
          </Container>
        </section>
      </RevealOnScroll>
    </div>
  );
}
