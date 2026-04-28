import Link from "next/link";

import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-black/10 bg-white/80 backdrop-blur dark:border-white/10 dark:bg-black/60">
      <Container>
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="font-semibold tracking-tight">
            Trading212 Bot
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              href="/pricing"
              className="hidden text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white sm:inline"
            >
              Pricing
            </Link>
            <Link
              href="/download"
              className="hidden text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white sm:inline"
            >
              Download
            </Link>
            <Link
              href="/faq"
              className="hidden text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white sm:inline"
            >
              FAQ
            </Link>
            <ButtonLink href="/login" variant="primary" className="h-10 px-4">
              Login
            </ButtonLink>
          </nav>
        </div>
      </Container>
    </header>
  );
}

