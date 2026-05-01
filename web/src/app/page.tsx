import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { BacktestChart } from "@/components/BacktestChart";
import { BacktestSummary } from "@/components/BacktestSummary";
import { FeaturePills } from "@/components/home/FeaturePills";
import { HeroSpotlightCard } from "@/components/home/HeroSpotlightCard";
import { RevealOnScroll } from "@/components/home/RevealOnScroll";
import { StepsAccordion } from "@/components/home/StepsAccordion";
import { Users } from "lucide-react";

export default function Home() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 -top-24 -z-10 h-[30rem] bg-[radial-gradient(70%_60%_at_50%_0%,rgba(56,189,248,0.18),transparent_65%)]" />

      <Container>
        <section className="scroll-mt-24 pb-16 pt-8 sm:scroll-mt-28 sm:pb-20 sm:pt-10">
          <RevealOnScroll>
            <div className="grid items-start gap-10 lg:grid-cols-12 lg:gap-12">
              <div
                id="results"
                className="order-2 scroll-mt-24 rounded-3xl border border-slate-800/70 bg-white/5 p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-sky-500/25 hover:bg-white/[0.07] hover:shadow-xl hover:shadow-sky-500/[0.07] sm:p-6 lg:order-1 lg:col-span-7"
              >
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-sm font-medium text-slate-200">Results (recent years)</div>
                    <div className="mt-1 text-xs text-slate-400">Monthly view · historical model output</div>
                  </div>
                </div>

                <div className="mt-5 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4 transition-colors duration-300 hover:border-slate-700/90">
                  <BacktestChart />
                </div>

                <div className="mt-4">
                  <BacktestSummary />
                </div>

                <p className="mt-4 text-center text-xs text-slate-500">
                  Shown for illustration — not a promise of live performance.
                </p>
              </div>

              <div id="overview" className="order-1 scroll-mt-24 lg:order-2 lg:col-span-5">
                <div className="inline-flex cursor-default items-center gap-2 rounded-full border border-slate-800/70 bg-white/5 px-3 py-1 text-xs text-slate-300 shadow-sm backdrop-blur transition-all duration-300 hover:border-sky-500/30 hover:bg-white/[0.08] hover:shadow-md hover:shadow-sky-500/5">
                  <span className="font-medium text-slate-50">Trading212 Bot</span>
                  <span className="text-slate-400">long-only · invest</span>
                </div>

                <h1 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
                  Automated investing on Trading212 — without a pro setup
                </h1>

                <HeroSpotlightCard>
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-5">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-500/25 text-sky-200 ring-1 ring-sky-400/30 transition-transform duration-300 group-hover/spot:scale-105 motion-reduce:transform-none">
                      <Users className="h-5 w-5" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold uppercase tracking-[0.12em] text-sky-200/90 sm:text-sm">
                        For everyday investors
                      </p>
                      <p className="mt-2 text-balance text-lg font-semibold leading-snug tracking-tight text-slate-50 sm:text-xl sm:leading-snug">
                        Your normal Trading212 Invest account is enough — no margin, no shorting, no special broker
                        setup.
                      </p>
                      <p className="mt-3 text-pretty text-sm leading-6 text-slate-200 sm:text-base sm:leading-7">
                        The bot is <span className="font-semibold text-white">long-only</span> and built around{" "}
                        <span className="font-semibold text-white">investing</span> (holding and adding over time),
                        not day-trading or complex products.
                      </p>
                      <FeaturePills />
                    </div>
                  </div>
                </HeroSpotlightCard>

                <p className="mt-6 max-w-lg text-pretty text-base leading-7 text-slate-300">
                  Sign in here for your subscription and license. A small Windows app on your PC connects to Trading212
                  locally so your API key never touches this website.
                </p>

                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <ButtonLink href="/login" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
                    Create account
                  </ButtonLink>
                  <ButtonLink href="/pricing" variant="secondary" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
                    View pricing
                  </ButtonLink>
                </div>

                <p className="mt-8 text-xs leading-5 text-slate-500">
                  Not financial advice. Trading involves risk; past results do not guarantee future returns.
                </p>
              </div>
            </div>
          </RevealOnScroll>
        </section>
      </Container>

      <Container>
        <section id="steps" className="scroll-mt-24 border-t border-slate-800/60 py-14 sm:scroll-mt-28 sm:py-20">
          <RevealOnScroll delayMs={80}>
            <StepsAccordion />
          </RevealOnScroll>
        </section>
      </Container>

      <Container>
        <section id="plans" className="scroll-mt-24 pb-20 sm:scroll-mt-28 sm:pb-24">
          <RevealOnScroll delayMs={120}>
            <div className="rounded-3xl bg-gradient-to-br from-sky-500/35 via-slate-700/40 to-violet-500/25 p-[1px] shadow-lg shadow-sky-500/5 transition-transform duration-300 hover:scale-[1.01] hover:shadow-sky-500/15 motion-reduce:transform-none motion-reduce:hover:transform-none">
              <div className="flex flex-col items-center justify-between gap-6 rounded-[calc(1.5rem-1px)] border border-slate-800/50 bg-slate-950/95 px-6 py-8 text-center backdrop-blur-sm transition-colors duration-300 hover:border-slate-700/70 hover:bg-slate-950/90 sm:flex-row sm:text-left">
                <div>
                  <div className="text-sm font-medium text-slate-200">Plans</div>
                  <p className="mt-1 text-sm text-slate-400">
                    Free to explore the portal · <span className="text-slate-200">Pro €49/mo</span> for live signals and
                    the executor.
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-3 sm:flex-row">
                  <ButtonLink href="/pricing" variant="secondary" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
                    Compare plans
                  </ButtonLink>
                  <ButtonLink href="/login" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
                    Go to login
                  </ButtonLink>
                </div>
              </div>
            </div>
          </RevealOnScroll>
        </section>
      </Container>
    </main>
  );
}
