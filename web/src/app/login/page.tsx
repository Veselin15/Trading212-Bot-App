import Link from "next/link";
import { redirect } from "next/navigation";

import { getServerUser } from "@/lib/supabase/server";
import { Container } from "@/components/ui/Container";
import { Card } from "@/components/ui/Card";

import { LoginForm } from "./ui";

export default async function LoginPage() {
  const user = await getServerUser();
  if (user) redirect("/dashboard");

  return (
    <main className="relative flex flex-1 items-center justify-center py-16">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(65%_60%_at_50%_0%,rgba(139,92,246,0.12),transparent_65%)]" />

      <Container>
        <div className="mx-auto w-full max-w-md">
          <Card className="p-8">
            <div className="text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Welcome back</h1>
              <p className="mt-2 text-sm text-slate-300">
                Sign in to manage your subscription, license key, and downloads.
              </p>
            </div>

            <div className="mt-8">
              <LoginForm />
            </div>

            <div className="mt-8 flex items-center justify-center gap-6 border-t border-white/10 pt-6 text-sm">
              <Link className="text-slate-400 transition-colors hover:text-violet-400" href="/">
                Home
              </Link>
              <Link className="text-slate-400 transition-colors hover:text-violet-400" href="/pricing">
                Pricing
              </Link>
            </div>
          </Card>
        </div>
      </Container>
    </main>
  );
}

