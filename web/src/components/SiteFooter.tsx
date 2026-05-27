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

export function SiteFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative mt-auto border-t border-white/[0.06] bg-background/50 py-12 backdrop-blur-sm">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"
        aria-hidden
      />
      <Container>
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr] md:gap-12 lg:grid-cols-[1.5fr_1fr_1fr]">
          <div className="space-y-4">
            <BrandLogo variant="footer" />
            <p className="max-w-sm text-sm leading-relaxed text-slate-400">
              Portal for subscriptions and signals. Your Trading212 API keys stay on your Windows desktop — never on
              this site.
            </p>
          </div>

          <div>
            <p className="section-eyebrow mb-4">Explore</p>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-1">
              {FOOTER_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    className="text-sm text-slate-400 transition-colors hover:text-emerald-300"
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
            <p className="text-xs leading-relaxed text-slate-500">
              Not financial advice. Trading involves risk of loss. Past performance does not guarantee future results.
            </p>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-white/[0.06] pt-8 sm:flex-row">
          <p className="text-sm text-slate-500">© {currentYear} SwiftTrade. All rights reserved.</p>
          <p className="font-mono text-xs text-slate-600">Signals in the cloud · execution on your machine</p>
        </div>
      </Container>
    </footer>
  );
}
