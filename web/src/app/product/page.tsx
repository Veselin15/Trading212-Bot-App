import { Activity, KeyRound, Layers, Lock, ShieldCheck, Workflow } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { Container } from "@/components/ui/Container";
import { Section } from "@/components/ui/Section";
import { ButtonLink } from "@/components/ui/Button";

const bullets = [
  {
    icon: Workflow,
    title: "Signal → execute architecture",
    body: "Signals are published to Supabase. Your desktop executor subscribes in real-time and places orders locally.",
  },
  {
    icon: Lock,
    title: "No broker keys on the website",
    body: "Your Trading212 API key is entered only inside the desktop app and stored encrypted on your machine.",
  },
  {
    icon: ShieldCheck,
    title: "Subscription gating + RLS",
    body: "Supabase Row Level Security limits access to the feed to active subscribers. The portal manages licensing.",
  },
  {
    icon: Layers,
    title: "Strategy stack (high level)",
    body: "Two-timeframe approach: a higher timeframe defines regime; a lower timeframe times entries and exits.",
  },
  {
    icon: Activity,
    title: "Risk controls",
    body: "Stop-loss and protective logic are enforced by the executor. Capital preservation is treated as a first-class goal.",
  },
  {
    icon: KeyRound,
    title: "License-based desktop access",
    body: "A per-user license key unlocks the executor. Pro users get download access plus the live feed.",
  },
];

export default function ProductPage() {
  return (
    <main className="relative overflow-hidden">
      <Container>
        <section className="py-16 sm:py-20">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-white/5 px-3 py-1 text-xs text-slate-300 backdrop-blur">
            <span className="font-medium text-slate-50">Product</span>
            <span className="text-slate-400">what you’re buying</span>
          </div>

          <h1 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
            A secure Trading212 automation stack — portal + desktop executor
          </h1>
          <p className="mt-4 max-w-2xl text-pretty text-base leading-7 text-slate-300">
            The portal is where you manage your account and subscription. The desktop app is what actually connects to
            Trading212 and executes orders. This split is intentional: it keeps broker credentials off the web.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <ButtonLink href="/pricing">See pricing</ButtonLink>
            <ButtonLink href="/faq" variant="secondary">
              Read FAQ
            </ButtonLink>
          </div>
        </section>
      </Container>

      <Section
        title="What’s included"
        lead="Everything you need to go from signup → licensed executor → realtime automation (Pro)."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {bullets.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-sm font-medium text-slate-50">{title}</div>
              </div>
              <div className="mt-3 text-sm leading-6 text-slate-300">{body}</div>
            </Card>
          ))}
        </div>
      </Section>

      <Section
        title="Setup in 5–10 minutes"
        lead="A clean, repeatable workflow — designed so you keep control while staying hands-off."
        id="setup"
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Step 1</div>
            <div className="mt-2 text-sm font-medium text-slate-50">Create your portal account</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">Sign up and verify email. Subscribe to Pro if needed.</div>
          </Card>
          <Card className="p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Step 2</div>
            <div className="mt-2 text-sm font-medium text-slate-50">Download the executor</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">Pro users can download the Windows desktop installer.</div>
          </Card>
          <Card className="p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Step 3</div>
            <div className="mt-2 text-sm font-medium text-slate-50">Connect Trading212 locally</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              Paste your Trading212 API key into the desktop app and choose paper/auto mode.
            </div>
          </Card>
        </div>

        <div className="mt-6 rounded-2xl border border-slate-800/70 bg-white/5 p-5 text-sm text-slate-300 backdrop-blur">
          Tip: start with paper/monitoring mode first, then enable full automation once you’re comfortable with behavior.
        </div>
      </Section>

      <Container>
        <section className="pb-16 sm:pb-20">
          <Card className="p-7">
            <h2 className="text-2xl font-semibold tracking-tight">Risk & disclaimer</h2>
            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
              <p>
                Trading is risky. This product is tooling (software) that can automate execution; it does not guarantee
                profits, and you can lose money.
              </p>
              <p>
                Backtests are simulations and can differ materially from live results due to slippage, spreads, outages,
                and market regime changes.
              </p>
              <p>
                Always review the settings and ensure the executor is running on hardware you control. You are
                responsible for your Trading212 account and decisions.
              </p>
            </div>
          </Card>
        </section>
      </Container>
    </main>
  );
}

