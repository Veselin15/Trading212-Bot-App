import Link from "next/link";
import { redirect } from "next/navigation";

import { getServerUser } from "@/lib/supabase/server";
import { BrandLogo } from "@/components/BrandLogo";
import { Container } from "@/components/ui/Container";
import { Card } from "@/components/ui/Card";

import { LoginForm } from "./ui";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const user = await getServerUser();
  if (user) redirect("/dashboard");

  const { error: oauthError } = await searchParams;

  return (
    <main className="relative flex flex-1 items-center justify-center py-16 lg:py-24">
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(65% 55% at 50% 0%, rgba(0,230,118,0.12), transparent 62%), radial-gradient(40% 30% at 80% 60%, rgba(16,185,129,0.06), transparent 55%)",
        }}
        aria-hidden
      />

      <Container>
        <div className="mx-auto w-full max-w-md">
          <Card className="glass-panel-strong border-white/[0.08] p-8 sm:p-10">
            <div className="flex justify-center">
              <BrandLogo variant="auth" />
            </div>
            <div className="mt-8 text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-white">Welcome back</h1>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                Sign in to manage your subscription, license key, and downloads.
              </p>
            </div>

            <div className="mt-8">
              <LoginForm oauthError={oauthError ?? null} />
            </div>

            <div className="mt-8 flex items-center justify-center gap-6 border-t border-white/10 pt-6 text-sm">
              <Link className="text-slate-400 transition-colors hover:text-emerald-400" href="/">
                Home
              </Link>
              <Link className="text-slate-400 transition-colors hover:text-emerald-400" href="/pricing">
                Pricing
              </Link>
            </div>
          </Card>
        </div>
      </Container>
    </main>
  );
}

