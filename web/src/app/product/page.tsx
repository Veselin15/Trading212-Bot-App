import { Container } from "@/components/ui/Container";
import { ArrowRightLeft, AlertTriangle, Database, Globe, Layers, Shield, Zap } from "lucide-react";

import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";

const features = [
  {
    icon: ArrowRightLeft,
    title: "Signal to execution",
    description: "Receive trading signals via Supabase Realtime and execute automatically on your Trading212 account.",
  },
  {
    icon: Shield,
    title: "Keys stay local",
    description: "Your Trading212 API key never leaves your PC. Desktop app handles all authentication locally.",
  },
  {
    icon: Database,
    title: "RLS-gated access",
    description: "Row-level security ensures you only receive signals your subscription tier allows.",
  },
  {
    icon: Globe,
    title: "EU universe + withholding",
    description: "Focus on European stocks with tax-efficient withholding considerations built-in.",
  },
  {
    icon: Layers,
    title: "Strategy stack",
    description: "Multi-factor models combining momentum, value, and quality signals for robust performance.",
  },
  {
    icon: AlertTriangle,
    title: "Risk controls",
    description: "Position sizing, stop-losses, and portfolio limits to protect your capital.",
  },
];

const setupSteps = [
  {
    step: 1,
    title: "Web portal",
    description: "Create account, upgrade to Pro, view your license key and subscription status.",
  },
  {
    step: 2,
    title: "Desktop app",
    description: "Download Windows app, paste Trading212 API key locally, enter license key from portal.",
  },
  {
    step: 3,
    title: "Monitoring",
    description: "Start with paper trading first. Monitor performance before switching to live execution.",
  },
];

export default function ProductPage() {
  return (
    <main>
      <Container className="py-20">
        <RevealOnScroll className="mx-auto mb-16 max-w-4xl text-center">
          <Badge className="mb-4 border-sky-500/30 text-sky-400">Product / what you&apos;re buying</Badge>
          <h1 className="mb-6 text-5xl">Portal + Desktop Executor</h1>
          <p className="mb-8 text-lg text-slate-300">
            Web portal manages your account and subscription. Desktop app executes trades locally on your PC. API keys
            never touch our servers.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <ButtonLink href="/pricing" className="bg-sky-600 hover:bg-sky-700">
              See pricing
            </ButtonLink>
            <ButtonLink href="/faq" variant="secondary">
              Read FAQ
            </ButtonLink>
          </div>
        </RevealOnScroll>

        <RevealOnScroll className="mb-20">
          <h2 className="mb-12 text-center text-3xl">What&apos;s included</h2>
          <div className="grid gap-6 md:grid-cols-2">
            {features.map((feature) => (
              <GlowHoverCard key={feature.title} className="p-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg border border-sky-500/30 bg-sky-500/10">
                    <feature.icon className="h-6 w-6 text-sky-400" />
                  </div>
                  <div>
                    <h3 className="mb-2 text-lg">{feature.title}</h3>
                    <p className="text-sm text-slate-400">{feature.description}</p>
                  </div>
                </div>
              </GlowHoverCard>
            ))}
          </div>
        </RevealOnScroll>

        <div id="setup">
          <RevealOnScroll className="mb-20">
            <h2 className="mb-12 text-center text-3xl">Setup in 5–10 minutes</h2>
            <div className="mb-8 grid gap-6 md:grid-cols-3">
              {setupSteps.map((item) => (
                <GlowHoverCard key={item.step} className="p-6">
                  <div className="mb-3 text-3xl text-sky-400">0{item.step}</div>
                  <h3 className="mb-2 text-lg">{item.title}</h3>
                  <p className="text-sm text-slate-400">{item.description}</p>
                </GlowHoverCard>
              ))}
            </div>

            <div className="mx-auto max-w-2xl rounded-xl border border-amber-500/30 bg-amber-500/10 p-6">
              <div className="flex items-start gap-3">
                <Zap className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-400" />
                <div>
                  <h4 className="mb-1 text-amber-400">Pro tip</h4>
                  <p className="text-sm text-slate-300">
                    Start with paper trading to monitor signal quality and test your setup before going live.
                  </p>
                </div>
              </div>
            </div>
          </RevealOnScroll>
        </div>

        <RevealOnScroll>
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center">
            <p className="text-sm text-slate-400">
              <strong className="text-slate-300">Disclaimer:</strong> Not financial or tax advice. Trading involves
              substantial risk. Past performance does not guarantee future results. Only invest what you can afford to
              lose. Consult professionals for your situation.
            </p>
          </div>
        </RevealOnScroll>
      </Container>
    </main>
  );
}
