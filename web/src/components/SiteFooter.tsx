import Link from "next/link";

import { BrandLogo } from "@/components/BrandLogo";
import { Container } from "@/components/ui/Container";

const FOOTER_LINKS = [
  { href: "/product", label: "Product" },
  { href: "/pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
  { href: "/download", label: "Download" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/login", label: "Sign in" },
] as const;

const LEGAL_LINKS = [
  { href: "/legal/terms", label: "Terms of Service" },
  { href: "/legal/privacy", label: "Privacy Policy" },
  { href: "/legal/risk", label: "Risk Disclosure" },
] as const;

const TRUST_STATS = [
  { value: "< 200ms", label: "Signal latency" },
  { value: "99.9%", label: "Uptime" },
  { value: "EU-listed", label: "Universe" },
  { value: "Local keys", label: "Security model" },
] as const;

export function SiteFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative mt-auto border-t border-white/[0.06]">
      {/* Trust stats row */}
      <div className="border-b border-white/[0.05] bg-white/[0.015]">
        <Container>
          <div className="grid grid-cols-2 gap-px md:grid-cols-4">
            {TRUST_STATS.map((s) => (
              <div key={s.label} className="py-5 text-center">
                <p className="font-mono text-sm font-semibold tabular-nums text-emerald-400">{s.value}</p>
                <p className="mt-0.5 text-xs text-slate-600">{s.label}</p>
              </div>
            ))}
          </div>
        </Container>
      </div>

      <div className="bg-background/50 py-12 backdrop-blur-sm">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent"
          aria-hidden
        />

        <Container>
          <div className="grid gap-10 md:grid-cols-[1.4fr_1fr] md:gap-12 lg:grid-cols-[1.5fr_1fr_1fr]">
            <div className="space-y-4">
              <BrandLogo variant="footer" />
              <p className="max-w-sm text-sm leading-relaxed text-slate-500">
                Portal for subscriptions and signals. Your Trading212 API keys stay on your Windows desktop — never on
                this site.
              </p>
              <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/8 px-3 py-1.5 w-fit">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
                <span className="text-xs font-medium text-emerald-400">Signals running</span>
              </div>
            </div>

            <div>
              <p className="section-eyebrow mb-4">Explore</p>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-1">
                {FOOTER_LINKS.map((link) => (
                  <li key={link.href}>
                    <Link
                      className="text-sm text-slate-500 transition-colors hover:text-emerald-400"
                      href={link.href}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="section-eyebrow mb-3 mt-7">Legal</p>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-1">
                {LEGAL_LINKS.map((link) => (
                  <li key={link.href}>
                    <Link
                      className="text-sm text-slate-500 transition-colors hover:text-emerald-400"
                      href={link.href}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div className="md:col-span-2 lg:col-span-1">
              <p className="section-eyebrow mb-4">Disclaimer</p>
              <p className="text-xs leading-relaxed text-slate-600">
                Not financial advice. Trading involves substantial risk of loss. Past performance does not guarantee
                future results. Tax treatment depends on your country — not tax advice. Only risk capital you can afford
                to lose.
              </p>
            </div>
          </div>

          <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-white/[0.05] pt-8 sm:flex-row">
            <p className="text-sm text-slate-600">© {currentYear} SwiftTrade. All rights reserved.</p>
            <p className="font-mono text-xs text-slate-700">Signals in the cloud · execution on your machine</p>
          </div>
        </Container>
      </div>
    </footer>
  );
}
