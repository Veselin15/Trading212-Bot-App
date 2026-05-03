import Link from "next/link";

import { BrandLogo } from "@/components/BrandLogo";
import { Container } from "@/components/ui/Container";

export function SiteFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-white/10 py-8">
      <Container>
        <div className="flex flex-col items-center justify-between gap-6 sm:flex-row sm:items-center">
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center sm:gap-4">
            <BrandLogo variant="footer" />
            <p className="text-center text-sm text-slate-400 sm:text-left">
              © {currentYear} SwiftTrade. All rights reserved.
            </p>
          </div>
          <div className="flex items-center gap-6">
            <Link className="text-sm text-slate-400 transition-colors hover:text-emerald-400" href="/dashboard">
              Dashboard
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-emerald-400" href="/product">
              Product
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-emerald-400" href="/pricing">
              Pricing
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-emerald-400" href="/faq">
              FAQ
            </Link>
          </div>
        </div>
      </Container>
    </footer>
  );
}

