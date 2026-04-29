import Link from "next/link";

import { Container } from "@/components/ui/Container";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-slate-800/60">
      <Container>
        <div className="flex flex-col gap-4 py-10 text-sm text-zinc-600 dark:text-zinc-400 sm:flex-row sm:items-center sm:justify-between">
          <div>© {new Date().getFullYear()} Trading212 Bot</div>
          <div className="flex items-center gap-4">
            <Link className="hover:text-zinc-900 dark:hover:text-white" href="/dashboard">
              Dashboard
            </Link>
            <Link className="hover:text-zinc-900 dark:hover:text-white" href="/pricing">
              Pricing
            </Link>
            <Link className="hover:text-zinc-900 dark:hover:text-white" href="/faq">
              FAQ
            </Link>
          </div>
        </div>
      </Container>
    </footer>
  );
}

