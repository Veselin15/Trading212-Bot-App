"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
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
import { HeroFlowDiagram } from "@/components/home/HeroFlowDiagram";
import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { StatsTicker } from "@/components/home/StatsTicker";
import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";

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

function HomeHeroCtas({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/login" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Create account <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/pricing" variant="secondary" className="border-slate-700 hover:border-slate-500">
          View pricing
        </ButtonLink>
      </div>
    );
  }

  if (mode.hasPro) {
    return (
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/dashboard" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Open dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/download" variant="secondary" className="border-slate-700 hover:border-slate-500">
          Download desktop app
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-3">
      {mode.checkoutEnabled ? (
        <form action="/api/stripe/checkout" method="post">
          <Button type="submit" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
            Upgrade to Pro <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      ) : (
        <ButtonLink href="/dashboard" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Go to dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
      )}
      <ButtonLink href="/pricing" variant="secondary" className="border-slate-700 hover:border-slate-500">
        Compare plans
      </ButtonLink>
    </div>
  );
}

function HomeHeroBadge({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <Badge className="border-emerald-500/40 bg-emerald-500/5 text-emerald-400">Integration ready</Badge>
    );
  }
  if (mode.hasPro) {
    return (
      <Badge className="border-emerald-500/40 bg-emerald-500/10 text-emerald-300">Pro active</Badge>
    );
  }
  return <Badge className="border-sky-500/40 bg-sky-500/10 text-sky-300">Signed in</Badge>;
}

function HomePricingCtas({ mode }: { mode: HomeCtaMode }) {
  if (mode.kind === "visitor") {
    return (
      <div className="flex flex-wrap justify-center gap-4">
        <ButtonLink href="/pricing" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Compare plans <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/login" variant="secondary" className="border-slate-700 hover:border-slate-500">
          Create free account
        </ButtonLink>
      </div>
    );
  }

  if (mode.hasPro) {
    return (
      <div className="flex flex-wrap justify-center gap-4">
        <ButtonLink href="/dashboard" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
        <ButtonLink href="/download" variant="secondary" className="border-slate-700 hover:border-slate-500">
          Download app
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap justify-center gap-4">
      {mode.checkoutEnabled ? (
        <form action="/api/stripe/checkout" method="post">
          <Button type="submit" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
            Upgrade to Pro <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      ) : (
        <ButtonLink href="/dashboard" className="gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
          Go to dashboard <ArrowRight className="h-4 w-4" />
        </ButtonLink>
      )}
      <ButtonLink href="/pricing" variant="secondary" className="border-slate-700 hover:border-slate-500">
        View pricing
      </ButtonLink>
    </div>
  );
}

export function HomeClient({ ctaMode }: { ctaMode: HomeCtaMode }) {
  return (
    <div className="relative overflow-x-hidden bg-slate-950 text-white">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[700px]"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 60% -10%, rgba(14,165,233,0.12) 0%, transparent 70%)",
        }}
      />

      <section className="relative pb-16 pt-20 lg:pb-20 lg:pt-28">
        <Container>
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
            <motion.div
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              className="max-w-xl space-y-7"
            >
              <HomeHeroBadge mode={ctaMode} />

              <h1 className="text-[2.7rem] leading-[1.12] tracking-tight lg:text-[3.4rem]">
                Automated investing on <span className="text-sky-400">Trading212</span> — without a pro setup
              </h1>

              <p className="max-w-md text-slate-400" style={{ fontSize: "1.05rem" }}>
                Signals and subscription live in the portal. Execution stays on your PC — your Trading212 API key never
                touches this website.
              </p>

              <HomeHeroCtas mode={ctaMode} />

              <p className="text-slate-600" style={{ fontSize: "0.72rem" }}>
                Not financial advice. Trading involves risk; past results do not guarantee future returns. Tax depends on
                your country — not tax advice.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
              className="flex justify-center lg:justify-end"
            >
              <HeroFlowDiagram />
            </motion.div>
          </div>
        </Container>
      </section>

      <StatsTicker />

      <RevealOnScroll>
        <section className="border-b border-slate-800/40 py-20">
          <Container>
            <div className="relative overflow-hidden rounded-3xl border border-slate-800/70 bg-white/[0.03] p-8 backdrop-blur sm:p-10">
              <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
              <div className="pointer-events-none absolute -right-24 -bottom-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

              <div className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500">How it works</p>
                  <h2 className="mt-2 text-3xl tracking-tight text-slate-50">Portal + executor, split by design</h2>
                </div>
                <p className="max-w-xl text-sm text-slate-400">
                  The website manages your account and subscription. The desktop app is the only component that stores
                  your Trading212 API key and places orders.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {HOW_IT_WORKS.map((step) => (
                  <div
                    key={step.n}
                    className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-6 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-sky-500/25 hover:shadow-[0_0_28px_-12px_rgba(56,189,248,0.18)] motion-reduce:hover:transform-none"
                  >
                    <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-sky-500/25 bg-sky-500/10 px-3 py-1">
                      <span className="font-mono text-xs text-sky-300">{step.n}</span>
                      <span className="text-xs text-slate-300">Step</span>
                    </div>
                    <h3 className="text-base font-medium text-slate-50">{step.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{step.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="border-b border-slate-800/40 py-16">
          <Container>
            <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
              {STATS_ROW.map((s) => (
                <div
                  key={s.label}
                  className="rounded-2xl border border-slate-800/70 bg-white/[0.03] p-6 text-center"
                >
                  <p className="mb-1 font-mono text-sky-400" style={{ fontSize: "1.9rem", fontWeight: 600 }}>
                    {s.value}
                  </p>
                  <p className="text-slate-500" style={{ fontSize: "0.78rem" }}>
                    {s.label}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-center text-slate-600" style={{ fontSize: "0.68rem" }}>
              Backtested results on historical data. Not a guarantee of future performance.
            </p>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="py-24">
          <Container>
            <div className="mb-14 max-w-xl">
              <Badge className="mb-4 border-sky-500/30 text-sky-400">Platform capabilities</Badge>
              <h2 className="text-4xl tracking-tight">Built for security-conscious traders</h2>
            </div>

            <motion.div
              className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
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
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-sky-500/20 bg-sky-500/10">
                        <f.icon className="h-5 w-5 text-sky-400" />
                      </div>
                      <div>
                        <h3 className="mb-2 leading-snug text-slate-50">{f.title}</h3>
                        <p className="text-slate-300/80" style={{ fontSize: "0.86rem" }}>
                          {f.desc}
                        </p>
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
        <section className="pb-24 py-8">
          <Container>
            <div className="relative grid items-center gap-10 overflow-hidden rounded-3xl border border-slate-800/60 bg-gradient-to-br from-slate-900/60 to-slate-950/60 p-10 md:grid-cols-2 md:p-14">
              <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
              <div>
                <div className="mb-4 flex items-center gap-2">
                  <Lock className="h-4 w-4 text-sky-400" />
                  <span className="text-xs uppercase tracking-wider text-sky-400">Security architecture</span>
                </div>
                <h2 className="mb-4 text-3xl tracking-tight">Your keys stay on your machine. Always.</h2>
                <p className="mb-6 text-slate-400" style={{ fontSize: "0.92rem" }}>
                  Trading212 Bot is split into two layers: a web portal for account and subscription management, and a
                  local Windows executor that holds your broker API keys. The portal <em>never</em> sees your
                  credentials.
                </p>
                <ButtonLink href="/product" variant="secondary" className="gap-2 border-slate-700 hover:border-sky-500">
                  Read the product overview <ArrowRight className="h-4 w-4" />
                </ButtonLink>
              </div>

              <div className="space-y-3">
                {[
                  {
                    icon: Cpu,
                    label: "Web Portal",
                    sub: "Account · Subscription · Signals",
                    border: "border-slate-700",
                    bg: "bg-slate-800/40",
                  },
                  {
                    icon: Lock,
                    label: "Desktop App",
                    sub: "API Keys · Order Executor · Local",
                    border: "border-sky-500/50",
                    bg: "bg-sky-950/30",
                  },
                ].map((row) => (
                  <div key={row.label} className={`flex items-center gap-4 rounded-xl border ${row.border} ${row.bg} p-4`}>
                    <row.icon className="h-5 w-5 flex-shrink-0 text-sky-400" />
                    <div>
                      <p className="text-slate-200" style={{ fontSize: "0.85rem" }}>
                        {row.label}
                      </p>
                      <p className="text-slate-500" style={{ fontSize: "0.72rem" }}>
                        {row.sub}
                      </p>
                    </div>
                  </div>
                ))}
                <div className="flex justify-center">
                  <div className="flex items-center gap-2 text-slate-600" style={{ fontSize: "0.7rem" }}>
                    <div className="h-4 w-px bg-slate-700" />
                    <span>one-way signal push · credentials never cross boundary</span>
                    <div className="h-4 w-px bg-slate-700" />
                  </div>
                </div>
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-28 py-8">
          <Container>
            <GlowHoverCard className="p-8 md:p-12 bg-slate-950/40">
              <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <Badge className="mb-3 border-sky-500/30 text-sky-400">Historical model output</Badge>
                  <h2 className="text-3xl tracking-tight">Strategy results</h2>
                  <p className="mt-1 text-slate-500" style={{ fontSize: "0.8rem" }}>
                    Monthly view · equity indexed to 100 at start
                  </p>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-emerald-400" style={{ fontSize: "0.78rem" }}>
                    Results (example)
                  </span>
                </div>
              </div>

              <motion.div
                className="rounded-2xl border border-slate-800/80 bg-slate-950/70 p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]"
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.45, ease: "easeOut" }}
              >
                <BacktestChart />
                <BacktestSummary />
              </motion.div>

              <p className="mt-5 text-slate-600" style={{ fontSize: "0.68rem" }}>
                Results shown are illustrative and not a guarantee of future performance. Your actual results will vary.
                This is not financial advice.
              </p>
            </GlowHoverCard>
          </Container>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-32 py-8">
          <Container>
            <div className="relative rounded-3xl bg-gradient-to-br from-sky-500 via-slate-700 to-violet-500 p-[1.5px]">
              <div className="relative overflow-hidden rounded-3xl bg-slate-950 p-10 text-center md:p-16">
                <div className="pointer-events-none absolute -left-20 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full bg-sky-500/10 blur-3xl" />
                <div className="pointer-events-none absolute -right-20 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full bg-violet-500/10 blur-3xl" />

                <Badge className="mb-6 border-sky-500/30 text-sky-400">Simple, transparent pricing</Badge>
                <h2 className="mb-4 text-4xl tracking-tight md:text-5xl">Start free. Go live when ready.</h2>
                <p className="mx-auto mb-8 max-w-lg text-slate-400" style={{ fontSize: "1rem" }}>
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
