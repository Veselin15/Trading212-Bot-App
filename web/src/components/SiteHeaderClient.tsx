"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";

import { BrandLogo } from "@/components/BrandLogo";
import { ButtonLink } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";

const BASE_NAV_LINKS = [
  { href: "/product", label: "Product" },
  { href: "/pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
] as const;

export function SiteHeaderClient({
  isAuthed,
  hasProAccess,
}: {
  isAuthed: boolean;
  hasProAccess: boolean;
}) {
  const pathname = usePathname() || "/";
  const [menuOpen, setMenuOpen] = useState(false);

  const navLinks = [
    ...BASE_NAV_LINKS.slice(0, 2),
    ...(hasProAccess ? ([{ href: "/download", label: "Download" }] as const) : []),
    ...BASE_NAV_LINKS.slice(2),
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-background/70 backdrop-blur-xl backdrop-saturate-150">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent"
        aria-hidden
      />
      <Container>
        <div className="flex h-[4.25rem] items-center justify-between">
          <BrandLogo variant="header" />

          <nav className="hidden items-center gap-0.5 md:flex">
            {navLinks.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
                    active ? "text-white" : "text-slate-400 hover:text-slate-100"
                  }`}
                >
                  {active ? (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-lg border border-emerald-500/20 bg-emerald-500/10 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]"
                      style={{ zIndex: -1 }}
                      transition={{ type: "spring", stiffness: 400, damping: 40 }}
                    />
                  ) : null}
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2.5 sm:gap-3">
            {!isAuthed ? (
              <>
                <Link href="/login" className="hidden sm:block">
                  <span className="inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white">
                    Log in
                  </span>
                </Link>
                <ButtonLink href="/login" className="h-10 px-4">
                  Get started
                </ButtonLink>
              </>
            ) : (
              <>
                <ButtonLink href="/dashboard" variant="secondary" className="h-10 px-4">
                  Dashboard
                </ButtonLink>
                <form action="/logout" method="post">
                  <button
                    type="submit"
                    className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] px-4 text-sm font-medium text-slate-200 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] transition-all hover:border-white/15 hover:bg-white/[0.08]"
                  >
                    Log out
                  </button>
                </form>
              </>
            )}

            <button
              type="button"
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white md:hidden"
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
            className="overflow-hidden border-t border-white/[0.06] bg-background/95 backdrop-blur-xl md:hidden"
          >
            <Container>
              <nav className="flex flex-col gap-1 py-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className={`rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
                      pathname === link.href
                        ? "border border-emerald-500/25 bg-emerald-500/10 text-white"
                        : "text-slate-400 hover:bg-white/[0.05] hover:text-white"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                {!isAuthed ? (
                  <div className="mt-2 border-t border-white/10 pt-3">
                    <ButtonLink href="/login" className="w-full">
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
