import { Container } from "@/components/ui/Container";

import { PricingTiers } from "./PricingTiers";

export default function PricingPage() {
  return (
    <main>
      <Container>
        <section className="py-16 sm:py-20">
          <div className="flex flex-col gap-3">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Pricing</h1>
            <p className="max-w-2xl text-sm leading-6 text-slate-300">
              The portal manages your account + license. The desktop executor handles Trading212 locally on your machine.
              When Stripe is enabled, checkout automatically activates Pro in Supabase.
            </p>
          </div>

          <PricingTiers />

          <div className="mt-10 rounded-2xl border border-slate-800/70 bg-white/5 p-5 text-sm text-slate-300 backdrop-blur transition-[border-color,box-shadow] duration-200 hover:border-sky-500/20 hover:shadow-[0_0_28px_-12px_rgba(56,189,248,0.15)]">
            Not financial advice. Trading involves risk. Past performance (including backtests) does not guarantee future
            results.
          </div>
        </section>
      </Container>
    </main>
  );
}
