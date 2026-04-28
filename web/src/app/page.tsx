import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16 font-sans dark:bg-black">
      <main className="w-full max-w-3xl rounded-2xl border border-black/10 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-zinc-950">
        <div className="flex flex-col gap-4">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
            Trading212 Bot
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Subscribe to receive strategy signals and execute them locally in the desktop app.
          </p>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
          >
            Login / Sign up
          </Link>
          <Link
            href="/account"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
          >
            Account
          </Link>
          <Link
            href="/download"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
          >
            Download desktop app
          </Link>
        </div>

        <div className="mt-10 rounded-xl border border-black/10 bg-zinc-50 p-4 text-sm text-zinc-700 dark:border-white/10 dark:bg-zinc-900/40 dark:text-zinc-300">
          This portal uses Supabase Auth for login and Stripe for subscriptions. Signal delivery is via Supabase
          Realtime.
        </div>
      </main>
    </div>
  );
}
