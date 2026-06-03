import type { Metadata } from "next";
import Link from "next/link";

import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";

export const metadata: Metadata = {
  title: "Legal — SwiftTrade",
  description: "Terms of Service, Privacy Policy, and Risk Disclosure for SwiftTrade.",
};

const DOCS = [
  {
    href: "/legal/terms",
    label: "Terms of Service",
    description:
      "The binding agreement between you and SwiftTrade governing use of the web portal and desktop app.",
  },
  {
    href: "/legal/privacy",
    label: "Privacy Policy",
    description:
      "What personal data we collect, why we collect it, who processes it, and how to exercise your GDPR rights.",
  },
  {
    href: "/legal/risk",
    label: "Risk Disclosure",
    description:
      "Mandatory risk warnings for automated trading software. Read this before enabling live execution.",
  },
] as const;

export default function LegalPage() {
  return (
    <main>
      <section className="relative border-b border-white/[0.06] pb-14 pt-14 lg:pb-18 lg:pt-18">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[360px] w-[700px] -translate-x-1/2 rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.1) 0%, transparent 70%)" }}
          aria-hidden
        />
        <Container>
          <div className="mx-auto max-w-2xl text-center">
            <SectionLabel className="mb-4 justify-center">Legal</SectionLabel>
            <h1 className="mb-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Legal documents
            </h1>
            <p className="text-base leading-relaxed text-slate-400">
              All agreements, policies, and disclosures that govern your use of SwiftTrade.
            </p>
          </div>
        </Container>
      </section>

      <section className="py-16 lg:py-20">
        <Container>
          <div className="mx-auto max-w-2xl space-y-4">
            {DOCS.map((doc) => (
              <Link
                key={doc.href}
                href={doc.href}
                className="group block rounded-2xl border border-white/[0.07] bg-[#060609]/80 p-6 transition-colors hover:border-white/[0.14] hover:bg-white/[0.03]"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-base font-semibold text-slate-100 transition-colors group-hover:text-white">
                      {doc.label}
                    </p>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{doc.description}</p>
                  </div>
                  <span className="shrink-0 text-slate-600 transition-colors group-hover:text-emerald-400">→</span>
                </div>
              </Link>
            ))}
          </div>
        </Container>
      </section>
    </main>
  );
}
