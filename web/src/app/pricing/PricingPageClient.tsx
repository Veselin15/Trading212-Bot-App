"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Check, Shield, ShieldCheck, Zap } from "lucide-react";

import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";

function AnimatedEuro({ amount }: { amount: number }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const steps = 28;
    const duration = 900;
    const increment = amount / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= amount) { setCount(amount); clearInterval(timer); }
      else setCount(Math.floor(current));
    }, duration / steps);
    return () => clearInterval(timer);
  }, [amount]);
  return <span>€{count}</span>;
}

export type ProTierCta = {
  loggedIn: boolean;
  checkoutEnabled: boolean;
  subscriptionActive: boolean;
};

function ProCtaButton({ proTier }: { proTier: ProTierCta }) {
  if (!proTier.loggedIn) return <ButtonLink href="/login" className="w-full">Upgrade to Pro</ButtonLink>;
  if (proTier.subscriptionActive) return <ButtonLink href="/dashboard" variant="secondary" className="w-full">Manage subscription</ButtonLink>;
  if (proTier.checkoutEnabled) return (
    <form action="/api/stripe/checkout" method="post" className="w-full">
      <Button type="submit" className="w-full">Upgrade to Pro</Button>
    </form>
  );
  return <ButtonLink href="/dashboard" variant="secondary" className="w-full">Go to dashboard</ButtonLink>;
}

const FREE_FEATURES = ["Live signals feed", "Paper trading on your practice account", "Full algorithm access", "No credit card required"] as const;
const PRO_FEATURES = ["Live trading signals", "Desktop app download", "License key activation", "Priority support", "Risk management tools"] as const;
const ENT_FEATURES = ["Custom signal strategies", "Multiple accounts", "Dedicated support", "SLA guarantees", "Custom integration"] as const;

const COMPARE_ROWS = [
  { label: "Signal access",         free: "Read-only / historical",  pro: "Live realtime",    ent: "Custom" },
  { label: "Desktop app",           free: "Paper mode only",          pro: "Full execution",   ent: "Custom" },
  { label: "License key",           free: "–",                        pro: "✓",                ent: "Multi-key" },
  { label: "API key storage",       free: "Local (PC)",               pro: "Local (PC)",       ent: "Local (PC)" },
  { label: "Signal latency",        free: "–",                        pro: "< 200ms",          ent: "< 200ms" },
  { label: "Support",               free: "Community",                pro: "Priority",         ent: "Dedicated + SLA" },
] as const;

export function PricingPageClient({ proTier }: { proTier: ProTierCta }) {
  return (
    <main>
      {/* ── Hero ── */}
      <section className="relative border-b border-white/[0.06] pb-16 pt-16 lg:pb-20 lg:pt-20">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[800px] -translate-x-1/2 rounded-full opacity-50 blur-3xl"
          style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.12) 0%, transparent 70%)" }}
          aria-hidden
        />
        <Container>
          <RevealOnScroll className="mx-auto max-w-2xl text-center">
            <SectionLabel className="mb-4 justify-center">Pricing</SectionLabel>
            <h1 className="mb-4 text-balance text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Transparent, no-surprise pricing
            </h1>
            <p className="text-base leading-relaxed text-slate-400 sm:text-lg">
              Powered by Stripe and Supabase. Start with a 14-day free trial — upgrade to Pro for live execution. Cancel anytime.
            </p>
          </RevealOnScroll>
        </Container>
      </section>

      <Container className="py-16 lg:py-20">

        {/* ── Tier cards ── */}
        <RevealOnScroll>
          <div className="mb-16 grid items-stretch gap-5 md:grid-cols-3">

            {/* Free */}
            <div className="flex flex-col rounded-2xl border border-white/[0.08] bg-[#07070b] p-7">
              <div className="mb-6">
                <p className="mb-1 text-lg font-bold text-white">14-Day Free Trial</p>
                <p className="text-sm text-slate-500">Full paper-trading access. No card required.</p>
              </div>
              <div className="mb-6 flex items-end gap-1">
                <span className="font-mono text-4xl font-semibold text-white">€0</span>
                <span className="mb-1 text-sm text-slate-500">for 14 days</span>
              </div>
              <ul className="mb-8 flex-1 space-y-3">
                {FREE_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                    <span className="text-sm text-slate-400">{f}</span>
                  </li>
                ))}
              </ul>
              <ButtonLink href="/login" variant="secondary" className="w-full">Start free trial</ButtonLink>
            </div>

            {/* Pro — featured */}
            <div className="relative rounded-[1.2rem] bg-gradient-to-br from-emerald-400/40 via-emerald-500/20 to-teal-500/35 p-px shadow-[0_0_60px_-16px_rgba(0,230,118,0.4)]">
              <div className="relative flex h-full flex-col overflow-hidden rounded-[calc(1.2rem-1px)] bg-[#060609] p-7">
                <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent" />
                <div className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-emerald-500/10 blur-3xl" />

                <div className="mb-6 flex items-start justify-between gap-3">
                  <div>
                    <p className="mb-1 text-lg font-bold text-white">Pro Automation</p>
                    <p className="text-sm text-slate-400">Full live automation with desktop execution</p>
                  </div>
                  <Badge className="shrink-0 border-emerald-500/40 bg-emerald-500/15 text-emerald-200">Popular</Badge>
                </div>

                <div className="mb-6 flex items-end gap-1">
                  <span className="font-mono text-4xl font-semibold text-white">
                    <AnimatedEuro amount={49} />
                  </span>
                  <span className="mb-1 text-sm text-slate-400">/mo</span>
                </div>

                <ul className="mb-8 flex-1 space-y-3">
                  {PRO_FEATURES.map((f) => (
                    <li key={f} className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
                        <Check className="h-2.5 w-2.5 text-emerald-400" strokeWidth={3} />
                      </div>
                      <span className="text-sm text-slate-200">{f}</span>
                    </li>
                  ))}
                </ul>

                <ProCtaButton proTier={proTier} />
                <p className="mt-4 text-center text-xs text-slate-600">
                  Trading212 API key stored only in desktop app
                </p>
              </div>
            </div>

            {/* Enterprise */}
            <div className="flex flex-col rounded-2xl border border-white/[0.08] bg-[#07070b] p-7">
              <div className="mb-6">
                <p className="mb-1 text-lg font-bold text-white">Enterprise</p>
                <p className="text-sm text-slate-500">Custom solutions for institutions</p>
              </div>
              <div className="mb-6">
                <span className="font-mono text-4xl font-semibold text-emerald-400">Custom</span>
              </div>
              <ul className="mb-8 flex-1 space-y-3">
                {ENT_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                    <span className="text-sm text-slate-400">{f}</span>
                  </li>
                ))}
              </ul>
              <a
                href="mailto:enterprise@trading212bot.example"
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.04] px-5 text-sm font-semibold text-slate-100 transition-all hover:border-white/[0.16] hover:bg-white/[0.08]"
              >
                Contact us <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </RevealOnScroll>

        {/* ── Trust indicators ── */}
        <RevealOnScroll>
          <div className="mb-16 flex flex-wrap justify-center gap-6 text-sm text-slate-500">
            {[
              { icon: ShieldCheck, label: "API keys never leave your PC" },
              { icon: Zap, label: "< 200ms signal latency" },
              { icon: Shield, label: "Cancel anytime, no lock-in" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <item.icon className="h-4 w-4 text-emerald-500/70" />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </RevealOnScroll>

        {/* ── Comparison table ── */}
        <RevealOnScroll>
          <div className="mb-12">
            <h2 className="mb-6 text-center text-xl font-semibold text-white">Compare plans</h2>
            <div className="overflow-hidden rounded-2xl border border-white/[0.07]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.07] bg-white/[0.02]">
                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Feature</th>
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Free</th>
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-emerald-400">Pro</th>
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARE_ROWS.map((row, i) => (
                    <tr key={row.label} className={`border-b border-white/[0.05] transition-colors hover:bg-white/[0.02] ${i === COMPARE_ROWS.length - 1 ? "border-0" : ""}`}>
                      <td className="px-5 py-3.5 font-medium text-slate-300">{row.label}</td>
                      <td className="px-5 py-3.5 text-center text-slate-500">{row.free}</td>
                      <td className="px-5 py-3.5 text-center font-semibold text-emerald-400">{row.pro}</td>
                      <td className="px-5 py-3.5 text-center text-slate-500">{row.ent}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </RevealOnScroll>

        {/* ── Disclaimer ── */}
        <RevealOnScroll>
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 text-center">
            <p className="text-xs leading-relaxed text-slate-600">
              <strong className="text-slate-500">Risk disclosure:</strong> Not financial advice. Trading carries
              substantial risk of loss. Past performance does not guarantee future results. Only risk capital you can
              afford to lose.
            </p>
          </div>
        </RevealOnScroll>
      </Container>
    </main>
  );
}
