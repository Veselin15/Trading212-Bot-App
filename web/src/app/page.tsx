import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { BacktestChart } from "@/components/BacktestChart";
import { Activity, Brain, Shield, TrendingUp } from "lucide-react";

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
                <span className="text-slate-400">signals → desktop executor</span>
              </div>

              <h1 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
                Algorithmic Trading for European Stocks
              </h1>

              <p className="mt-4 max-w-xl text-pretty text-base leading-7 text-slate-300">
                Connect once, then let the strategy stream signals through Supabase. Your desktop app executes orders
                locally using encrypted Trading212 keys—no broker credentials on the web.
              </p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
                <ButtonLink href="/login">Start Free Trial</ButtonLink>
                <ButtonLink href="/pricing" variant="secondary">
                  View Performance
                </ButtonLink>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Low latency</div>
                  <div className="mt-1 text-sm text-slate-300">Signals stream in milliseconds.</div>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Local security</div>
                  <div className="mt-1 text-sm text-slate-300">Keys stay encrypted on your PC.</div>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-4 backdrop-blur">
                  <div className="text-sm font-medium text-slate-50">Access control</div>
                  <div className="mt-1 text-sm text-slate-300">Subscription-gated with RLS.</div>
                </div>
              </div>
            </div>

            {/* Mockup / abstract chart placeholder */}
            <div className="lg:col-span-6">
              <div className="relative overflow-hidden rounded-3xl border border-slate-800/70 bg-white/5 p-6 shadow-sm">
                <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-sky-500/10 blur-3xl" />
                <div className="relative">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-slate-200">Live readiness</div>
                    <div className="rounded-full border border-slate-800/70 bg-slate-950/50 px-2 py-1 text-xs text-slate-300">
                      Connect & Forget
                    </div>
                  </div>

                  <div className="mt-5 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4">
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                      <span>Heartbeat:</span>
                      <span className="font-mono text-emerald-300">PONG</span>
                    </div>

                    <div className="mt-4">
                      <svg viewBox="0 0 520 220" className="h-auto w-full">
                        {/* Grid */}
                        <g stroke="rgba(148,163,184,0.25)" strokeWidth="1">
                          {Array.from({ length: 6 }).map((_, i) => {
                            const y = 20 + i * 32;
                            return <line key={i} x1="40" x2="500" y1={y} y2={y} />;
                          })}
                          {Array.from({ length: 8 }).map((_, i) => {
                            const x = 40 + i * 60;
                            return <line key={i} y1="20" y2="205" x1={x} x2={x} />;
                          })}
                        </g>

                        {/* Curve (dummy) */}
                        <path
                          d="M40 185 C90 165, 130 150, 170 132 C210 114, 260 100, 300 86 C340 72, 390 58, 430 45 C460 35, 480 28, 500 22"
                          fill="none"
                          stroke="#38bdf8"
                          strokeWidth="3"
                          strokeLinecap="round"
                        />

                        {/* Glow */}
                        <path
                          d="M40 185 C90 165, 130 150, 170 132 C210 114, 260 100, 300 86 C340 72, 390 58, 430 45 C460 35, 480 28, 500 22"
                          fill="none"
                          stroke="#38bdf8"
                          strokeWidth="9"
                          opacity="0.12"
                          strokeLinecap="round"
                        />

                        {/* Endpoint marker */}
                        <circle cx="500" cy="22" r="7" fill="#38bdf8" opacity="0.95" />
                      </svg>
                    </div>

                    <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                      <span>Signals</span>
                      <span className="font-mono text-slate-200">subscribed</span>
                      <span>Executor: local</span>
                    </div>
                  </div>

                  <div className="mt-5 rounded-2xl border border-slate-800/70 bg-white/5 p-4">
                    <div className="font-mono text-xs text-slate-300">
                      HELLO → WELCOME → PING/PONG
                      <br />
                      SIGNAL(payload) → local execution
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </Container>

      {/* The Engine */}
      <Container>
        <section className="pb-16 sm:pb-20">
          <div className="grid gap-10 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-4">
              <h2 className="text-3xl font-semibold tracking-tight">The Engine</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Institutional-grade logic, explained conceptually—without exposing exact indicators or parameters.
              </p>
            </div>

            <div className="lg:col-span-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Macro Trend Alignment</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    The algorithm first analyzes the broader market direction. It acts as a primary filter, ensuring we
                    only deploy capital when the underlying asset has a mathematically proven upward trajectory.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Activity className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Momentum Exhaustion</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    We don&apos;t buy breakouts. The system waits for temporary pullbacks and uses custom momentum oscillators
                    to pinpoint the exact millisecond selling pressure fades.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Brain className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">AI Sentiment Gatekeeper</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Technical analysis isn&apos;t enough. The engine pings real-time LLM sentiment analysis to block entries
                    during high-volatility macroeconomic events or negative earnings calls.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      <Shield className="h-5 w-5" />
                    </div>
                    <div className="text-sm font-medium text-slate-50">Ruthless Risk Management</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Capital preservation is the ultimate priority. Every trade has a hard-coded algorithmic stop-loss.
                    Once in profit, the system dynamically trails a break-even stop to protect your principal.
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
                A “connect & forget” flow designed for trust, low risk, and local execution.
              </p>
            </div>

            <div className="lg:col-span-8">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      1
                    </div>
                    <div className="text-sm font-medium text-slate-50">Create Account</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Sign in with email/password (or Google) via Supabase Auth.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      2
                    </div>
                    <div className="text-sm font-medium text-slate-50">Download App</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Get the desktop client and keep Trading212 keys encrypted on your machine.
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                      3
                    </div>
                    <div className="text-sm font-medium text-slate-50">Connect API</div>
                  </div>
                  <div className="mt-3 text-sm text-slate-300">
                    Generate your Trading212 API key and paste it into the desktop app.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </Container>

      {/* Performance / Social proof */}
      <Container>
        <section className="pb-16 sm:pb-20">
          <div className="rounded-3xl border border-slate-800/70 bg-white/5 p-6 shadow-sm sm:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-3xl font-semibold tracking-tight">Performance preview</h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                  Dummy chart for now. Your real results come from the live strategy and your subscription state.
                </p>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3 text-center">
                  <div className="text-xs text-slate-400">Simulated</div>
                  <div className="mt-1 text-3xl font-semibold tracking-tight text-emerald-300">+29% APY</div>
                </div>
              </div>
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
                      Designed around steady execution cadence and subscription gating.
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                    <div className="text-sm font-medium text-slate-50">Local execution</div>
                    <div className="mt-2 text-sm text-slate-300">
                      Your Trading212 keys remain encrypted on-device. Web only coordinates signals.
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                    <div className="text-sm font-medium text-slate-50">Secure access</div>
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
              Start with Paper Trading for free, then upgrade to Pro Automation when you want fully automated execution.
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
                  Start Free Trial
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
                  Stripe checkout and webhooks will activate Pro subscription status in Supabase.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-slate-800/70 bg-white/5 p-5 text-sm text-slate-300">
            No Trading212 API key is collected on the website. The desktop app accepts it locally during setup.
          </div>
        </section>
      </Container>
    </main>
  );
}
