import Link from "next/link";
import { Container } from "@/components/ui/Container";

interface LegalDocHeaderProps {
  title: string;
  subtitle: string;
  effectiveDate: string;
}

export function LegalDocHeader({ title, subtitle, effectiveDate }: LegalDocHeaderProps) {
  return (
    <section className="relative border-b border-white/[0.06] pb-14 pt-14 lg:pb-18 lg:pt-18">
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[360px] w-[700px] -translate-x-1/2 rounded-full opacity-40 blur-3xl"
        style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.1) 0%, transparent 70%)" }}
        aria-hidden
      />
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Link
            href="/legal"
            className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-white/[0.1] bg-white/[0.04] px-3 py-1.5 text-xs text-slate-400 transition-colors hover:text-slate-200"
          >
            ← Legal documents
          </Link>
          <h1 className="mb-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">{title}</h1>
          <p className="text-base text-slate-400">{subtitle}</p>
          <p className="mt-3 text-xs text-slate-600">Effective date: {effectiveDate}</p>
        </div>
      </Container>
    </section>
  );
}

interface LegalSectionProps {
  num: number;
  heading: string;
  children: React.ReactNode;
}

export function LegalSection({ num, heading, children }: LegalSectionProps) {
  return (
    <section className="border-b border-white/[0.05] pb-8 pt-8 first:pt-0 last:border-0">
      <h2 className="mb-4 text-lg font-semibold tracking-tight text-slate-100">
        <span className="mr-2 font-mono text-sm text-emerald-500">{num}.</span>
        {heading}
      </h2>
      <div className="space-y-3 text-sm leading-relaxed text-slate-400">{children}</div>
    </section>
  );
}

export function LegalWarningBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.07] p-4 text-sm leading-relaxed text-amber-200">
      {children}
    </div>
  );
}

export function LegalInfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-sky-500/25 bg-sky-500/[0.07] p-4 text-sm leading-relaxed text-sky-200">
      {children}
    </div>
  );
}

export function LegalList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-400">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function LegalDocLayout({ children }: { children: React.ReactNode }) {
  return (
    <main>
      {children}
      <section className="py-12">
        <Container>
          <div className="mx-auto max-w-3xl rounded-2xl border border-white/[0.07] bg-[#060609]/80 p-6 text-center">
            <p className="mb-1 text-sm font-semibold text-slate-200">Questions about these terms?</p>
            <p className="text-sm text-slate-500">
              Email{" "}
              <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                legal@swifttrade.app
              </a>{" "}
              and we will respond within 5 business days.
            </p>
          </div>
        </Container>
      </section>
    </main>
  );
}
