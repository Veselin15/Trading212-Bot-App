"use client";

import { useEffect, useState } from "react";

import { Check } from "lucide-react";

import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";

function AnimatedEuro({ amount }: { amount: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const increment = amount / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= amount) {
        setCount(amount);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
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
  if (!proTier.loggedIn) {
    return (
      <ButtonLink href="/login" className="w-full bg-emerald-600 hover:bg-emerald-400">
        Upgrade to Pro
      </ButtonLink>
    );
  }
  if (proTier.subscriptionActive) {
    return (
      <ButtonLink href="/dashboard" variant="secondary" className="w-full">
        Manage subscription
      </ButtonLink>
    );
  }
  if (proTier.checkoutEnabled) {
    return (
      <form action="/api/stripe/checkout" method="post" className="w-full">
        <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-400">
          Upgrade to Pro
        </Button>
      </form>
    );
  }
  return (
    <ButtonLink href="/dashboard" variant="secondary" className="w-full">
      Go to dashboard
    </ButtonLink>
  );
}

type PricingTier =
  | {
      kind: "link";
      name: string;
      price: number | null;
      description: string;
      features: readonly string[];
      cta: string;
      href: string;
      accent: boolean;
      popular?: boolean;
      footnote?: string;
    }
  | {
      kind: "pro";
      name: string;
      price: number;
      description: string;
      features: readonly string[];
      accent: boolean;
      popular?: boolean;
      footnote?: string;
    }
  | {
      kind: "mailto";
      name: string;
      price: number | null;
      description: string;
      features: readonly string[];
      cta: string;
      href: string;
      accent: boolean;
    };

const tiers: PricingTier[] = [
  {
    kind: "link",
    name: "Paper / Free",
    price: 0,
    description: "Explore the platform with paper trading",
    features: ["View signals (read-only)", "Paper trading simulation", "Historical performance data", "Community support"],
    cta: "Start free",
    href: "/login",
    accent: false,
  },
  {
    kind: "pro",
    name: "Pro Automation",
    price: 49,
    description: "Full automation with desktop execution",
    features: [
      "Live trading signals",
      "Desktop app download",
      "License key activation",
      "Priority support",
      "Risk management tools",
    ],
    accent: true,
    popular: true,
    footnote: "Trading212 API key stored only in desktop app",
  },
  {
    kind: "mailto",
    name: "Enterprise",
    price: null,
    description: "Custom solutions for institutions",
    features: ["Custom signal strategies", "Multiple accounts", "Dedicated support", "SLA guarantees", "Custom integration"],
    cta: "Contact",
    href: "mailto:enterprise@trading212bot.example",
    accent: false,
  },
];

export function PricingPageClient({ proTier }: { proTier: ProTierCta }) {
  return (
    <main>
      <Container className="py-20">
        <RevealOnScroll className="mx-auto mb-16 max-w-3xl text-center">
          <h1 className="mb-6 text-5xl">Pricing</h1>
          <p className="text-lg text-slate-300">
            Transparent pricing powered by Stripe and Supabase. Start free, upgrade when ready. Cancel anytime.
          </p>
        </RevealOnScroll>

        <div className="mb-12 grid gap-8 md:grid-cols-3">
          {tiers.map((tier) => (
            <RevealOnScroll key={tier.name}>
              <GlowHoverCard className="relative flex h-full flex-col p-8" disableLift={false}>
                {tier.kind === "pro" && tier.popular ? (
                  <Badge className="absolute right-4 top-4 bg-emerald-600 text-slate-50">Most popular</Badge>
                ) : null}

                <div className="mb-6">
                  <h3 className="mb-2 text-2xl">{tier.name}</h3>
                  <p className="text-sm text-slate-400">{tier.description}</p>
                </div>

                <div className="mb-6">
                  {tier.price !== null ? (
                    <div className="text-4xl">
                      <AnimatedEuro amount={tier.price} />
                      <span className="text-lg text-slate-400">/mo</span>
                    </div>
                  ) : (
                    <div className="text-4xl text-emerald-400">Custom</div>
                  )}
                </div>

                <ul className="mb-8 flex-1 space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-400" />
                      <span className="text-sm text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                {tier.kind === "pro" ? (
                  <ProCtaButton proTier={proTier} />
                ) : tier.kind === "mailto" ? (
                  <a
                    href={tier.href}
                    className={`inline-flex h-11 w-full items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors ${
                      tier.accent
                        ? "bg-emerald-600 text-slate-950 shadow-sm shadow-emerald-500/20 hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/60"
                        : "border border-white/10 bg-white/5 text-slate-50 backdrop-blur hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/10"
                    }`}
                  >
                    {tier.cta}
                  </a>
                ) : (
                  <ButtonLink
                    href={tier.href}
                    variant={tier.accent ? "primary" : "secondary"}
                    className={tier.accent ? "w-full bg-emerald-600 hover:bg-emerald-400" : "w-full"}
                  >
                    {tier.cta}
                  </ButtonLink>
                )}

                {tier.kind !== "mailto" && tier.footnote ? (
                  <p className="mt-4 text-center text-xs text-slate-500">{tier.footnote}</p>
                ) : null}
              </GlowHoverCard>
            </RevealOnScroll>
          ))}
        </div>

        <RevealOnScroll>
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center">
            <p className="text-sm text-slate-400">
              <strong className="text-slate-300">Risk disclosure:</strong> Not financial advice. Trading carries
              substantial risk of loss. Only risk capital you can afford to lose.
            </p>
          </div>
        </RevealOnScroll>
      </Container>
    </main>
  );
}
