import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { BacktestChart } from "@/components/BacktestChart";
import { BacktestSummary } from "@/components/BacktestSummary";
import { SetupFlow } from "@/components/SetupFlow";
import { Activity, Lock, Shield, TrendingUp, Workflow } from "lucide-react";

export default function Home() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 -top-24 -z-10 h-[30rem] bg-[radial-gradient(70%_60%_at_50%_0%,rgba(56,189,248,0.18),transparent_65%)]" />

      {/* Hero */}
      <Container>
        <section className="pb-16 pt-14 sm:pb-20 sm:pt-20">
          <div className="grid items-center gap-10 lg:grid-cols-12">
            <div className="lg:col-span-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-white/5 px-3 py-1 text-xs text-slate-300 backdrop-blur">
                <span className="font-medium text-slate-50">Trading212 Bot</span>
                <span className="text-slate-400">portal + licensed desktop executor</span>
              </div>

              <h1 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
                A safer way to automate Trading212 execution
              </h1>

              <p className="mt-4 max-w-xl text-pretty text-base leading-7 text-slate-300">
                The portal manages your account, subscription, and license key. The Windows desktop app connects to
                Trading212 locally and executes orders on your machine — so broker keys never touch the website.
              </p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
                <ButtonLink href="/login">Create account</ButtonLink>
                <ButtonLink href="/product" variant="secondary">
                  See how it works
                </ButtonLink>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Local execution</div>
                  <div className="mt-1 text-sm text-slate-300">Orders are placed from your desktop.</div>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Local security</div>
                  <div className="mt-1 text-sm text-slate-300">Trading212 keys stay encrypted on-device.</div>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Licensed access</div>
                  <div className="mt-1 text-sm text-slate-300">Subscriptions gate the feed + downloads.</div>
                </div>
              </div>
            </div>

            {/* Proof block: real backtest curve + execution model */}
            <div className="lg:col-span-6">
              <div className="relative overflow-hidden rounded-3xl border border-slate-800/70 bg-white/5 p-6 shadow-sm">
                <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl" />
                <div className="relative">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="text-sm font-medium text-slate-200">Backtest preview</div>
                      <div className="mt-1 text-xs text-slate-400">Monthly aggregation • simulated results</div>
                    </div>
                    <div className="rounded-full border border-slate-800/70 bg-slate-950/50 px-2 py-1 text-xs text-slate-300">
                      Hover for exact values
                    </div>
                  </div>

                  <div className="mt-5 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4">
                    <BacktestChart />
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                      <span>Start: $10k</span>
                      <span className="font-mono text-slate-200">backtest_equity.json</span>
                      <span>End: derived from data</span>
                    </div>
                  </div>

                  <div className="mt-5">
                    <BacktestSummary />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </Container>

      {/* Architecture */}
      <Container>
        <section className="pb-16 sm:pb-20">
          <div className="grid gap-10 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-4">
              <h2 className="text-3xl font-semibold tracking-tight">Designed for trust</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                The portal handles licensing and access. The desktop executor handles Trading212 locally. This split keeps
                broker credentials out of the browser and out of the backend.
              </p>
            </div>

            <div className="lg:col-span-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Workflow className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Signal → execute architecture</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Signals are published to Supabase in real-time. Your desktop app subscribes and places orders locally.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Lock className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">No broker keys on the website</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Your Trading212 API key is entered only in the desktop executor and stored encrypted on your machine.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Strategy stack (high level)</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Two-timeframe approach: a higher timeframe defines regime; a lower timeframe times entries/exits.
                    Exact indicators/parameters are intentionally not exposed.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Shield className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Risk controls</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Stop-loss and protective behavior are enforced by the executor so risk handling is part of the runtime.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </Container>

      {/* How it works */}
      <Container>
        <section id="features" className="pb-16 sm:pb-20">
          <div className="grid gap-10 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-4">
              <h2 className="text-3xl font-semibold tracking-tight">How it works</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                A simple, repeatable setup. Start in paper/monitoring mode, then enable automation when you’re ready.
              </p>
            </div>

            <div className="lg:col-span-8">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      1
                    </div>
                    <div className="text-sm font-medium text-slate-50">Create account</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Sign in to access subscription status, license key, and downloads.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      2
                    </div>
                    <div className="text-sm font-medium text-slate-50">Download executor</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Pro users download the Windows desktop app that performs execution.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      3
                    </div>
                    <div className="text-sm font-medium text-slate-50">Connect Trading212 locally</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Paste your Trading212 API key into the desktop app and enter your license key.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8">
            <SetupFlow />
          </div>
        </section>
      </Container>

      {/* Backtest */}
      <Container>
        <section className="pb-16 sm:pb-20">
          <div className="rounded-3xl border border-slate-800/70 bg-white/5 p-6 shadow-sm sm:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-3xl font-semibold tracking-tight">Backtest preview</h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                  This is simulated performance (monthly aggregation). Live results can differ due to slippage, spreads,
                  outages, and market regime changes.
                </p>
              </div>

              <ButtonLink href="/pricing" variant="secondary">
                See pricing
              </ButtonLink>
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-12 lg:items-center">
              <div className="lg:col-span-8">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4 sm:p-6">
                  <BacktestChart />
                </div>
              </div>

              <div className="lg:col-span-4">
                <div className="space-y-3">
                  <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                    <div className="text-sm font-medium text-slate-50">Compound growth</div>
                    <div className="mt-2 text-sm text-slate-300">
                      Evaluated as a system (signals + execution cadence), not as a single “magic trade”.
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                    <div className="text-sm font-medium text-slate-50">Local execution</div>
                    <div className="mt-2 text-sm text-slate-300">
                      Your Trading212 keys remain encrypted on-device. Web only coordinates signals.
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                    <div className="text-sm font-medium text-slate-50">Access gating</div>
                    <div className="mt-2 text-sm text-slate-300">
                      Supabase RLS keeps reads scoped to active subscriptions.
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </section>
      </Container>

      {/* Pricing */}
      <Container>
        <section className="pb-16 sm:pb-20">
          <div className="flex flex-col gap-3">
            <h2 className="text-3xl font-semibold tracking-tight">Pricing</h2>
            <p className="max-w-2xl text-sm leading-6 text-slate-300">
              Start free to explore the portal, then upgrade to Pro for the live feed and desktop downloads.
            </p>
          </div>

          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-800/70 bg-white/5 p-7 shadow-sm">
              <div className="text-sm font-medium text-slate-300">Paper Trading / Free</div>
              <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">€0</div>
              <div className="mt-2 text-sm text-slate-300">Explore the flow through the portal.</div>

              <ul className="mt-6 space-y-2 text-sm text-slate-200">
                <li>Portal access</li>
                <li>Account + license management</li>
                <li>Desktop download (gated)</li>
              </ul>

              <div className="mt-7">
                <ButtonLink href="/login" variant="secondary" className="w-full sm:w-auto">
                  Start free
                </ButtonLink>
              </div>
            </div>

            <div className="relative overflow-hidden rounded-3xl border border-sky-500/40 bg-sky-500/10 p-7 shadow-sm">
              <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-sky-500/20 blur-3xl" />
              <div className="relative">
                <div className="text-sm font-medium text-sky-200">Pro Automation / €49/mo</div>
                <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">€49</div>
                <div className="mt-2 text-sm text-slate-300">Realtime signals + automated desktop execution.</div>

                <ul className="mt-6 space-y-2 text-sm text-slate-200">
                  <li>Signals feed (RLS gated)</li>
                  <li>License key for the executor</li>
                  <li>Desktop download access</li>
                </ul>

                <div className="mt-7">
                  <ButtonLink href="/login" className="w-full sm:w-auto">
                    Upgrade to Pro
                  </ButtonLink>
                </div>

                <div className="mt-4 text-xs text-slate-400">
                  Stripe checkout activates Pro in Supabase and unlocks the feed + downloads.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-slate-800/70 bg-white/5 p-5 text-sm text-slate-300">
            Not financial advice. Trading is risky. No Trading212 API key is collected on the website — the desktop app
            accepts it locally during setup.
          </div>
        </section>
      </Container>
    </main>
  );
}
