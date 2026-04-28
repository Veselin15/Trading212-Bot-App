import Link from "next/link";
import { redirect } from "next/navigation";

import { getServerUser } from "@/lib/supabase/server";

import { LoginForm } from "./ui";

export default async function LoginPage() {
  const user = await getServerUser();
  if (user) redirect("/account");

  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <div className="w-full max-w-md rounded-2xl border border-black/10 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-zinc-950">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Login</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Sign in or create an account to manage your subscription and downloads.
          </p>
        </div>

        <div className="mt-6">
          <LoginForm />
        </div>

        <div className="mt-6 text-sm text-zinc-600 dark:text-zinc-400">
          <Link className="underline hover:text-zinc-900 dark:hover:text-zinc-200" href="/">
            Back to home
          </Link>
        </div>
      </div>
    </main>
  );
}

