import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { Section } from "@/components/ui/Section";

import { ProductDisclaimer } from "./ProductDisclaimer";
import { ProductFeatureGrid, ProductSetupGrid } from "./ProductGrids";

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
        <ProductFeatureGrid />
      </Section>

      <Section
        title="Setup in 5–10 minutes"
        lead="A clean, repeatable workflow — designed so you keep control while staying hands-off."
        id="setup"
      >
        <ProductSetupGrid />

        <div className="mt-6 rounded-2xl border border-slate-800/70 bg-white/5 p-5 text-sm text-slate-300 backdrop-blur">
          Tip: start with paper/monitoring mode first, then enable full automation once you’re comfortable with behavior.
        </div>
      </Section>

      <Container>
        <section className="pb-16 sm:pb-20">
          <ProductDisclaimer />
        </section>
      </Container>
    </main>
  );
}
