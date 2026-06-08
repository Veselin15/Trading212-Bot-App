"use client";

import { useEffect, useState } from "react";
import { Check, Shield, ShieldCheck, Zap } from "lucide-react";

import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";
import type { EffectiveTier } from "@/lib/tier";

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

export type PricingCta = {
  loggedIn: boolean;
  checkoutEnabled: boolean;
  currentTier: EffectiveTier | null;
};

/** CTA for a specific paid plan, aware of what the user already has. */
function PlanCta({ plan, cta }: { plan: "starter" | "pro"; cta: PricingCta }) {
  const label = plan === "starter" ? "Get Starter" : "Get Pro";

  if (!cta.loggedIn) {
    return <ButtonLink href="/login" className="w-full">{label}</ButtonLink>;
  }
  // Already on this exact (or higher) tier.
  if (cta.currentTier === "PRO" || (plan === "starter" && cta.currentTier === "STARTER")) {
    return <ButtonLink href="/dashboard" variant="secondary" className="w-full">Manage subscription</ButtonLink>;
  }
  const isUpgrade = plan === "pro" && cta.currentTier === "STARTER";
  if (cta.checkoutEnabled) {
    return (
      <form action="/api/stripe/checkout" method="post" className="w-full">
        <input type="hidden" name="plan" value={plan} />
        <Button type="submit" className="w-full">{isUpgrade ? "Upgrade to Pro" : label}</Button>
      </form>
    );
  }
  return <ButtonLink href="/dashboard" variant="secondary" className="w-full">Go to dashboard</ButtonLink>;
}

const TRIAL_FEATURES = [
  "Full signal feed (paper mode)",
  "Paper trading on your practice account",
  "Up to 3 concurrent positions",
  "Desktop app + license key",
  "No credit card required",
] as const;
const STARTER_FEATURES = [
  "Live (real-money) auto-execution",
  "Core signals — our highest-confidence picks",
  "Up to 3 concurrent positions",
  "Email support",
] as const;
const PRO_FEATURES = [
  "Live (real-money) auto-execution",
  "Full signal feed — every opportunity",
  "Up to 10 concurrent positions",
  "Priority support",
] as const;

const COMPARE_ROWS = [
  { label: "Price",                    trial: "Free · 14 days", starter: "€19/mo",        pro: "€49/mo" },
  { label: "Live real-money trading",  trial: "–",              starter: "✓",             pro: "✓" },
  { label: "Paper trading",            trial: "✓",              starter: "✓",             pro: "✓" },
  { label: "Signal feed",              trial: "Full (paper)",   starter: "Core only",     pro: "Full feed" },
  { label: "Concurrent positions",     trial: "3 (paper)",      starter: "3",             pro: "10" },
  { label: "Desktop app + license",    trial: "✓",              starter: "✓",             pro: "✓" },
  { label: "Support",                  trial: "Community",      starter: "Email",         pro: "Priority" },
] as const;

export function PricingPageClient({ cta }: { cta: PricingCta }) {
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
              Start free. Go live when you&apos;re ready.
            </h1>
            <p className="text-base leading-relaxed text-slate-400 sm:text-lg">
              Try the full algorithm in paper mode for 14 days — no card. Then pick Starter for our highest-conviction
              core signals, or Pro for the complete signal feed and more concurrent positions. Cancel anytime.
            </p>
          </RevealOnScroll>
        </Container>
      </section>

      <Container className="py-16 lg:py-20">

        {/* ── Tier cards ── */}
        <RevealOnScroll>
          <div className="mb-16 grid items-stretch gap-5 md:grid-cols-3">

            {/* Free trial */}
            <div className="flex flex-col rounded-2xl border border-white/[0.08] bg-[#07070b] p-7">
              <div className="mb-6">
                <p className="mb-1 text-lg font-bold text-white">14-Day Free Trial</p>
                <p className="text-sm text-slate-500">Evaluate the full algorithm. No card required.</p>
              </div>
              <div className="mb-6 flex items-end gap-1">
                <span className="font-mono text-4xl font-semibold text-white">€0</span>
                <span className="mb-1 text-sm text-slate-500">for 14 days</span>
              </div>
              <ul className="mb-8 flex-1 space-y-3">
                {TRIAL_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
                    <span className="text-sm text-slate-400">{f}</span>
                  </li>
                ))}
              </ul>
              <ButtonLink href="/login" variant="secondary" className="w-full">Start free trial</ButtonLink>
            </div>

            {/* Starter */}
            <div className="flex flex-col rounded-2xl border border-sky-500/[0.18] bg-[#07070b] p-7">
              <div className="mb-6">
                <p className="mb-1 text-lg font-bold text-white">Starter</p>
                <p className="text-sm text-slate-500">Go live on our highest-conviction signals</p>
              </div>
              <div className="mb-6 flex items-end gap-1">
                <span className="font-mono text-4xl font-semibold text-white">
                  <AnimatedEuro amount={19} />
                </span>
                <span className="mb-1 text-sm text-slate-500">/mo</span>
              </div>
              <ul className="mb-8 flex-1 space-y-3">
                {STARTER_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2.5">
                    <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-sky-500/20">
                      <Check className="h-2.5 w-2.5 text-sky-300" strokeWidth={3} />
                    </div>
                    <span className="text-sm text-slate-300">{f}</span>
                  </li>
                ))}
              </ul>
              <PlanCta plan="starter" cta={cta} />
            </div>

            {/* Pro — featured */}
            <div className="relative rounded-[1.2rem] bg-gradient-to-br from-emerald-400/40 via-emerald-500/20 to-teal-500/35 p-px shadow-[0_0_60px_-16px_rgba(0,230,118,0.4)]">
              <div className="relative flex h-full flex-col overflow-hidden rounded-[calc(1.2rem-1px)] bg-[#060609] p-7">
                <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent" />
                <div className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-emerald-500/10 blur-3xl" />

                <div className="mb-6 flex items-start justify-between gap-3">
                  <div>
                    <p className="mb-1 text-lg font-bold text-white">Pro</p>
                    <p className="text-sm text-slate-400">The complete signal feed, full firepower</p>
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

                <PlanCta plan="pro" cta={cta} />
                <p className="mt-4 text-center text-xs text-slate-600">
                  Trading212 API key stored only in desktop app
                </p>
                <p className="mt-2 text-center text-xs text-slate-700">
                  By subscribing you agree to our{" "}
                  <a href="/legal/terms" className="underline hover:text-slate-500">Terms of Service</a>
                  {" "}and{" "}
                  <a href="/legal/risk" className="underline hover:text-slate-500">Risk Disclosure</a>.
                </p>
              </div>
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
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">Trial</th>
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-sky-300">Starter</th>
                    <th className="px-5 py-3.5 text-center text-xs font-semibold uppercase tracking-wide text-emerald-400">Pro</th>
                  </tr>
                </thead>
                <tbody>
                  {COMPARE_ROWS.map((row, i) => (
                    <tr key={row.label} className={`border-b border-white/[0.05] transition-colors hover:bg-white/[0.02] ${i === COMPARE_ROWS.length - 1 ? "border-0" : ""}`}>
                      <td className="px-5 py-3.5 font-medium text-slate-300">{row.label}</td>
                      <td className="px-5 py-3.5 text-center text-slate-500">{row.trial}</td>
                      <td className="px-5 py-3.5 text-center text-sky-300/90">{row.starter}</td>
                      <td className="px-5 py-3.5 text-center font-semibold text-emerald-400">{row.pro}</td>
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
