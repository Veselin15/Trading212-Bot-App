import Link from "next/link";

import { Container } from "@/components/ui/Container";

export function SiteFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-slate-800 py-8">
      <Container>
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-sm text-slate-400">© {currentYear} Trading212 Bot. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link className="text-sm text-slate-400 transition-colors hover:text-sky-400" href="/dashboard">
              Dashboard
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-sky-400" href="/product">
              Product
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-sky-400" href="/pricing">
              Pricing
            </Link>
            <Link className="text-sm text-slate-400 transition-colors hover:text-sky-400" href="/faq">
              FAQ
            </Link>
          </div>
        </div>
      </Container>
    </footer>
  );
}

