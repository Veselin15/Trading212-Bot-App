import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-white font-sans text-zinc-950 dark:bg-black dark:text-zinc-50">
      <header className="border-b border-black/10 dark:border-white/10">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="font-semibold tracking-tight">
            Trading212 Bot
          </Link>
          <nav className="flex items-center gap-2">
            <Link
              href="/download"
              className="hidden text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white sm:inline"
            >
              Download
            </Link>
            <Link
              href="/account"
              className="hidden text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white sm:inline"
            >
              Account
            </Link>
            <Link
              href="/login"
              className="inline-flex h-10 items-center justify-center rounded-xl bg-zinc-950 px-4 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
            >
              Login
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-6 py-14">
        <section className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div className="flex flex-col gap-5">
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Signals delivered instantly. Execution stays local.
            </h1>
            <p className="text-base leading-7 text-zinc-600 dark:text-zinc-300">
              The strategy runs continuously and inserts signals into Supabase. Your desktop app listens in realtime and
              executes trades using your locally encrypted Trading212 keys.
            </p>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/login"
                className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
              >
                Get started
              </Link>
              <Link
                href="/download"
                className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
              >
                Download app
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-black/10 bg-zinc-50 p-6 shadow-sm dark:border-white/10 dark:bg-zinc-950">
            <div className="text-sm font-medium">How it works</div>
            <div className="mt-4 grid gap-3 text-sm text-zinc-700 dark:text-zinc-300">
              <div className="rounded-xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                <div className="font-medium">1) Login</div>
                <div className="mt-1 text-zinc-600 dark:text-zinc-400">Supabase Auth (email/password or Google).</div>
              </div>
              <div className="rounded-xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                <div className="font-medium">2) Subscribe (later)</div>
                <div className="mt-1 text-zinc-600 dark:text-zinc-400">Stripe will mark your subscription active.</div>
              </div>
              <div className="rounded-xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                <div className="font-medium">3) Execute locally</div>
                <div className="mt-1 text-zinc-600 dark:text-zinc-400">
                  Desktop listens to signals and places orders from your machine.
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-14 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-black/10 p-5 dark:border-white/10">
            <div className="text-sm font-medium">Realtime signals</div>
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
              Supabase Realtime broadcasts new rows in milliseconds.
            </div>
          </div>
          <div className="rounded-2xl border border-black/10 p-5 dark:border-white/10">
            <div className="text-sm font-medium">Local security</div>
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
              Trading212 keys stay encrypted on your machine.
            </div>
          </div>
          <div className="rounded-2xl border border-black/10 p-5 dark:border-white/10">
            <div className="text-sm font-medium">Access control</div>
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
              RLS allows reads only for active subscribers.
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-auto border-t border-black/10 dark:border-white/10">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6 text-sm text-zinc-600 dark:text-zinc-400">
          <div>© {new Date().getFullYear()} Trading212 Bot</div>
          <div className="flex items-center gap-4">
            <Link className="hover:text-zinc-900 dark:hover:text-white" href="/account">
              Account
            </Link>
            <Link className="hover:text-zinc-900 dark:hover:text-white" href="/download">
              Download
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
