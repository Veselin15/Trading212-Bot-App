import {
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  CheckCircle2,
  Cloud,
  Database,
  Globe,
  Layers,
  Lock,
  Monitor,
  Shield,
  Zap,
} from "lucide-react";

import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";

const FEATURES = [
  {
    icon: ArrowRightLeft,
    title: "Signal to execution",
    desc: "Receive trading signals via Supabase Realtime and execute automatically on your Trading212 account.",
    tone: "emerald" as const,
    tag: "Core",
  },
  {
    icon: Shield,
    title: "Keys stay local",
    desc: "Your Trading212 API key never leaves your PC. The desktop app handles all broker authentication locally.",
    tone: "gold" as const,
    tag: "Security",
  },
  {
    icon: Database,
    title: "RLS-gated access",
    desc: "Row-level security policies ensure you only receive signals your subscription tier allows.",
    tone: "sky" as const,
    tag: "Platform",
  },
  {
    icon: Globe,
    title: "25-stock EU universe",
    desc: "Covers EUR-denominated blue-chips across defense, luxury, semiconductors, pharma, and financials. Tax withholding handling built-in.",
    tone: "sky" as const,
    tag: "Strategy",
  },
  {
    icon: Layers,
    title: "ML ensemble strategy",
    desc: "XGBoost + LightGBM ensemble across 25 EU stocks. SwingStrategyV3 with trend-scaled take-profits, macro regime sizing, and sector clamping.",
    tone: "emerald" as const,
    tag: "Alpha",
  },
  {
    icon: AlertTriangle,
    title: "Risk controls",
    desc: "Position sizing, stop-losses, and portfolio limits enforced at the executor level to protect your capital.",
    tone: "gold" as const,
    tag: "Risk",
  },
];

const SETUP = [
  {
    n: "01",
    title: "Create your portal account",
    desc: "Sign up on the web portal, choose your plan, and retrieve your desktop license key from the dashboard.",
    time: "~2 min",
  },
  {
    n: "02",
    title: "Install the desktop executor",
    desc: "Download the Windows app. Paste your Trading212 API key locally and enter the license key from the portal.",
    time: "~5 min",
  },
  {
    n: "03",
    title: "Paper trade first, then go live",
    desc: "Start in monitoring mode to verify signal quality. Switch to live execution when you're confident.",
    time: "Your call",
  },
];

const TONE = {
  emerald: {
    icon: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400 shadow-[0_0_18px_-4px_rgba(0,230,118,0.3)]",
    tag: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    hover: "hover:border-emerald-500/25 hover:shadow-[0_16px_40px_-20px_rgba(0,230,118,0.2)]",
  },
  gold: {
    icon: "border-amber-500/30 bg-amber-500/15 text-amber-400 shadow-[0_0_18px_-4px_rgba(245,158,11,0.3)]",
    tag: "border-amber-500/20 bg-amber-500/10 text-amber-400",
    hover: "hover:border-amber-500/25 hover:shadow-[0_16px_40px_-20px_rgba(245,158,11,0.18)]",
  },
  sky: {
    icon: "border-sky-500/30 bg-sky-500/15 text-sky-400 shadow-[0_0_18px_-4px_rgba(56,189,248,0.3)]",
    tag: "border-sky-500/20 bg-sky-500/10 text-sky-400",
    hover: "hover:border-sky-500/25 hover:shadow-[0_16px_40px_-20px_rgba(56,189,248,0.18)]",
  },
};

export default function ProductPage() {
  return (
    <main>
      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b border-white/[0.06] pb-20 pt-16 lg:pb-24 lg:pt-20">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[500px] w-[900px] -translate-x-1/2 rounded-full opacity-60 blur-3xl"
          style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.14) 0%, transparent 70%)" }}
          aria-hidden
        />
        <Container>
          <div className="mx-auto max-w-3xl text-center">
            <RevealOnScroll>
              <Badge className="mb-5 border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                Product overview
              </Badge>
              <h1 className="mb-5 text-balance text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-[3.25rem]">
                <span className="text-gradient-hero">Portal +</span>{" "}
                <span className="text-gradient-brand">Desktop Executor</span>
              </h1>
              <p className="mx-auto mb-8 max-w-2xl text-base leading-relaxed text-slate-400 sm:text-lg">
                The web portal manages your account and subscription. The desktop app executes trades locally — your
                Trading212 API key never touches our servers.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <ButtonLink href="/pricing" className="gap-2">
                  See pricing <ArrowRight className="h-4 w-4" />
                </ButtonLink>
                <ButtonLink href="/faq" variant="secondary">
                  Read FAQ
                </ButtonLink>
              </div>
            </RevealOnScroll>

            {/* Key facts row */}
            <RevealOnScroll>
              <div className="mt-12 flex flex-wrap justify-center gap-3">
                {[
                  { label: "API keys never leave your PC" },
                  { label: "Supabase Realtime signals" },
                  { label: "Long-only EU strategy" },
                  { label: "Setup in under 10 min" },
                ].map((f) => (
                  <span
                    key={f.label}
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500/70" />
                    {f.label}
                  </span>
                ))}
              </div>
            </RevealOnScroll>
          </div>
        </Container>
      </section>

      {/* ── Architecture ── */}
      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-20 lg:py-24">
          <Container>
            <div className="mb-12 text-center">
              <SectionLabel className="justify-center">Architecture</SectionLabel>
              <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Two layers, one seamless flow
              </h2>
            </div>

            <div className="mx-auto grid max-w-4xl gap-4 md:grid-cols-2">
              {[
                {
                  icon: Cloud,
                  zone: "Cloud Portal",
                  color: "sky" as const,
                  items: ["Account & subscription management", "Signal generation & delivery", "License key issuance", "Stripe billing via RLS-gated access"],
                  note: "No API keys — ever",
                  noteDot: "bg-rose-500/60",
                },
                {
                  icon: Monitor,
                  zone: "Desktop Executor",
                  color: "emerald" as const,
                  items: ["Stores your Trading212 API key locally", "Subscribes to live signals", "Places orders directly to Trading212", "Paper-trade mode for safe testing"],
                  note: "Keys never cross the boundary",
                  noteDot: "bg-emerald-400/70",
                },
              ].map((layer) => {
                const c = layer.color === "sky"
                  ? { border: "border-sky-500/25", bg: "bg-sky-500/[0.07]", icon: "border-sky-500/30 bg-sky-500/15 text-sky-300", label: "text-sky-400" }
                  : { border: "border-emerald-500/25", bg: "bg-emerald-500/[0.07]", icon: "border-emerald-500/30 bg-emerald-500/15 text-emerald-300", label: "text-emerald-400" };
                return (
                  <div key={layer.zone} className={`relative overflow-hidden rounded-2xl border p-6 ${c.border} ${c.bg}`}>
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />
                    <div className="mb-5 flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${c.icon}`}>
                        <layer.icon className="h-5 w-5" strokeWidth={1.75} />
                      </div>
                      <span className={`text-sm font-bold ${c.label}`}>{layer.zone}</span>
                    </div>
                    <ul className="space-y-2.5">
                      {layer.items.map((item) => (
                        <li key={item} className="flex items-start gap-2.5 text-sm text-slate-300">
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                          {item}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-5 flex items-center gap-2 border-t border-white/[0.06] pt-4">
                      <span className={`h-1.5 w-1.5 rounded-full ${layer.noteDot}`} />
                      <span className="text-xs text-slate-600">{layer.note}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Security boundary caption */}
            <div className="mx-auto mt-5 flex max-w-sm items-center justify-center gap-3">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
              <div className="flex items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/8 px-3 py-1.5">
                <Lock className="h-3 w-3 text-amber-400" />
                <span className="text-xs font-semibold text-amber-400/80">Security boundary</span>
              </div>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Features ── */}
      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-20 lg:py-24">
          <Container>
            <div className="mb-12">
              <SectionLabel>What&apos;s included</SectionLabel>
              <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Everything in the box
              </h2>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((f) => {
                const t = TONE[f.tone];
                return (
                  <div
                    key={f.title}
                    className={`group relative rounded-2xl border border-white/[0.07] bg-[#060609]/80 p-5 transition-all duration-300 hover:-translate-y-0.5 ${t.hover} motion-reduce:hover:transform-none`}
                  >
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-2xl bg-gradient-to-r from-transparent via-white/8 to-transparent" />

                    <div className="mb-4 flex items-start justify-between gap-2">
                      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${t.icon}`}>
                        <f.icon className="h-5 w-5" strokeWidth={1.75} />
                      </div>
                      <span className={`rounded-full border px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide ${t.tag}`}>
                        {f.tag}
                      </span>
                    </div>

                    <h3 className="mb-1.5 text-sm font-bold text-slate-50">{f.title}</h3>
                    <p className="text-[0.8rem] leading-relaxed text-slate-400">{f.desc}</p>
                  </div>
                );
              })}
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── Setup ── */}
      <RevealOnScroll>
        <section className="border-b border-white/[0.06] py-20 lg:py-24" id="setup">
          <Container>
            <div className="mb-12">
              <SectionLabel>Getting started</SectionLabel>
              <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Live in under 10 minutes
              </h2>
            </div>

            <div className="relative grid gap-4 md:grid-cols-3">
              {/* Connecting line on desktop */}
              <div
                className="pointer-events-none absolute inset-x-[calc(33%/2)] top-[2.75rem] hidden h-px md:block"
                style={{ background: "linear-gradient(90deg, transparent 0%, rgba(16,185,129,0.2) 20%, rgba(16,185,129,0.2) 80%, transparent 100%)" }}
                aria-hidden
              />

              {SETUP.map((step) => (
                <div
                  key={step.n}
                  className="group relative rounded-2xl border border-white/[0.07] bg-[#060609]/80 p-6 transition-all duration-300 hover:border-emerald-500/25 hover:bg-[#08080c] hover:shadow-[0_16px_40px_-20px_rgba(0,230,118,0.18)] motion-reduce:hover:transform-none"
                >
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-2xl bg-gradient-to-r from-transparent via-white/8 to-transparent" />
                  <div className="mb-5 flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_18px_-4px_rgba(0,230,118,0.3)]">
                      <span className="font-mono text-xs font-bold text-emerald-300">{step.n}</span>
                    </div>
                    <span className="rounded-full border border-white/[0.07] bg-white/[0.03] px-2.5 py-1 text-[0.65rem] text-slate-500">
                      {step.time}
                    </span>
                  </div>
                  <h3 className="mb-2 font-semibold leading-snug text-slate-50">{step.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-400">{step.desc}</p>
                </div>
              ))}
            </div>

            {/* Pro tip */}
            <div className="mt-6 flex items-start gap-3 rounded-2xl border border-amber-500/25 bg-amber-500/[0.07] p-5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/15">
                <Zap className="h-4 w-4 text-amber-400" strokeWidth={1.75} />
              </div>
              <div>
                <p className="mb-1 text-sm font-semibold text-amber-300">Start with paper trading</p>
                <p className="text-sm leading-relaxed text-slate-400">
                  Monitor signal quality and verify your setup in paper mode before enabling live execution. You can
                  switch at any time from within the desktop app.
                </p>
              </div>
            </div>
          </Container>
        </section>
      </RevealOnScroll>

      {/* ── CTA ── */}
      <RevealOnScroll>
        <section className="py-20 lg:py-24">
          <Container>
            <div className="mx-auto max-w-2xl text-center">
              <SectionLabel className="justify-center">Ready to start?</SectionLabel>
              <h2 className="mb-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Start free, go live when ready
              </h2>
              <p className="mb-8 text-slate-400">
                Paper trading is free forever. Upgrade to Pro for live signals, a desktop license, and full automation.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <ButtonLink href="/pricing" className="gap-2">
                  View pricing <ArrowRight className="h-4 w-4" />
                </ButtonLink>
                <ButtonLink href="/login" variant="secondary">
                  Create free account
                </ButtonLink>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="mt-16 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 text-center">
              <p className="text-xs leading-relaxed text-slate-600">
                <strong className="text-slate-500">Disclaimer:</strong> Not financial or tax advice. Trading involves
                substantial risk. Past performance does not guarantee future results. Only invest capital you can afford
                to lose. Consult a professional for your specific situation.
              </p>
            </div>
          </Container>
        </section>
      </RevealOnScroll>
    </main>
  );
}
