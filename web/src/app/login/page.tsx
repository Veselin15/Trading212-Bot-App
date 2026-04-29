import Link from "next/link";
import { redirect } from "next/navigation";

import { getServerUser } from "@/lib/supabase/server";

import { LoginForm } from "./ui";

export default async function LoginPage() {
  const user = await getServerUser();
  if (user) redirect("/dashboard");

  return (
    <main className="relative flex flex-1 items-center justify-center px-6 py-16">
      <div className="pointer-events-none absolute inset-x-0 -top-24 -z-10 h-[26rem] bg-[radial-gradient(65%_60%_at_50%_0%,rgba(24,24,27,0.12),transparent_65%)] dark:bg-[radial-gradient(65%_60%_at_50%_0%,rgba(244,244,245,0.10),transparent_65%)]" />

      <div className="w-full max-w-md overflow-hidden rounded-3xl border border-black/10 bg-white/70 shadow-sm backdrop-blur dark:border-white/10 dark:bg-black/30">
        <div className="p-8">
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Welcome back</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              Sign in to manage your subscription, license key, and downloads.
            </p>
          </div>

          <div className="mt-6">
            <LoginForm />
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-black/10 bg-zinc-50/60 px-8 py-5 text-sm dark:border-white/10 dark:bg-black/20">
          <Link className="text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white" href="/">
            Home
          </Link>
          <Link className="text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white" href="/pricing">
            Pricing
          </Link>
        </div>
      </div>
    </main>
  );
}

