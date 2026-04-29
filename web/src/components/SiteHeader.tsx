import Link from "next/link";

import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { getServerUser } from "@/lib/supabase/server";

export async function SiteHeader() {
  const user = await getServerUser();
  const isAuthed = Boolean(user);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-800/60 bg-slate-950/70 backdrop-blur">
      <Container>
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="font-semibold tracking-tight">
            Trading212 Bot
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              href="/pricing"
              className="hidden text-sm text-slate-300 hover:text-white sm:inline"
            >
              Pricing
            </Link>
            <Link
              href="/download"
              className="hidden text-sm text-slate-300 hover:text-white sm:inline"
            >
              Download
            </Link>
            <Link
              href="/faq"
              className="hidden text-sm text-slate-300 hover:text-white sm:inline"
            >
              FAQ
            </Link>

            {!isAuthed ? (
              <ButtonLink href="/login" variant="primary" className="h-10 px-4">
                Login
              </ButtonLink>
            ) : (
              <>
                <ButtonLink href="/dashboard" variant="secondary" className="h-10 px-4">
                  Dashboard
                </ButtonLink>
                <form action="/logout" method="post">
                  <button className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-800/80 bg-white/5 px-4 text-sm font-medium text-slate-50 transition-colors hover:bg-white/10">
                    Log out
                  </button>
                </form>
              </>
            )}
          </nav>
        </div>
      </Container>
    </header>
  );
}

