"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X, Zap } from "lucide-react";

import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";

const NAV_LINKS = [
  { href: "/product", label: "Product" },
  { href: "/pricing", label: "Pricing" },
  { href: "/download", label: "Download" },
  { href: "/faq", label: "FAQ" },
];

export function SiteHeaderClient({ isAuthed }: { isAuthed: boolean }) {
  const pathname = usePathname() || "/";
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <Container>
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="group flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-sky-500/30 bg-sky-500/15 transition-colors group-hover:bg-sky-500/25">
              <Zap className="h-3.5 w-3.5 text-sky-400" />
            </div>
            <span
              className="tracking-tight text-white"
              style={{ fontSize: "1rem", fontWeight: 600, letterSpacing: "-0.01em" }}
            >
              Trading212 <span className="text-sky-400">Bot</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative rounded-lg px-3.5 py-2 text-sm transition-colors ${
                    active ? "text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {active ? (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-lg bg-slate-800/70"
                      style={{ zIndex: -1 }}
                      transition={{ type: "spring", stiffness: 400, damping: 40 }}
                    />
                  ) : null}
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            {!isAuthed ? (
              <>
                <Link href="/login" className="hidden sm:block">
                  <span className="inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white">
                    Log in
                  </span>
                </Link>
                <ButtonLink href="/login" className="h-10 bg-sky-500 px-4 text-slate-950 hover:bg-sky-400">
                  Get started
                </ButtonLink>
              </>
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

            <button
              className="rounded-lg p-1.5 text-slate-400 transition-colors hover:text-white md:hidden"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </Container>

      <AnimatePresence>
        {menuOpen ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-slate-800/60 md:hidden"
          >
            <Container>
              <nav className="flex flex-col gap-1 py-4">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className={`rounded-lg px-4 py-2.5 text-sm transition-colors ${
                      pathname === link.href
                        ? "bg-slate-800 text-white"
                        : "text-slate-400 hover:bg-slate-800/50 hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                {!isAuthed ? (
                  <div className="mt-2 border-t border-slate-800 pt-2">
                    <ButtonLink href="/login" className="w-full bg-sky-500 text-slate-950 hover:bg-sky-400">
                      Get started
                    </ButtonLink>
                  </div>
                ) : null}
              </nav>
            </Container>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}

