export default function Home() {
  return (
    <main className="relative">
      <div className="pointer-events-none absolute inset-x-0 -top-24 -z-10 h-[28rem] bg-[radial-gradient(70%_60%_at_50%_0%,rgba(24,24,27,0.14),transparent_65%)] dark:bg-[radial-gradient(70%_60%_at_50%_0%,rgba(244,244,245,0.12),transparent_65%)]" />

      <div className="mx-auto w-full max-w-6xl px-6 py-16 sm:py-20">
        <section className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div className="flex flex-col gap-6">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-black/10 bg-white/60 px-3 py-1 text-xs text-zinc-700 backdrop-blur dark:border-white/10 dark:bg-black/30 dark:text-zinc-300">
              <span className="font-medium text-zinc-900 dark:text-zinc-50">Trading212 Bot</span>
              <span className="text-zinc-500 dark:text-zinc-400">signals → desktop executor</span>
            </div>

            <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
              Realtime trading signals, with execution that stays on your machine.
            </h1>
            <p className="max-w-xl text-pretty text-base leading-7 text-zinc-600 dark:text-zinc-300">
              The strategy publishes signals to Supabase. Your desktop executor listens and places orders locally using
              encrypted Trading212 keys—so your credentials never live on a server.
            </p>

            <div className="flex flex-col gap-3 sm:flex-row">
              <a
                href="/login"
                className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white shadow-sm shadow-black/10 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
              >
                Get started
              </a>
              <a
                href="/pricing"
                className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 bg-white/60 px-5 text-sm font-medium text-zinc-950 backdrop-blur hover:bg-white dark:border-white/10 dark:bg-black/30 dark:text-zinc-50 dark:hover:bg-black/50"
              >
                View pricing
              </a>
            </div>

            <div className="grid gap-4 pt-2 sm:grid-cols-3">
              <div className="rounded-2xl border border-black/10 bg-white/70 p-4 backdrop-blur dark:border-white/10 dark:bg-black/30">
                <div className="text-sm font-medium">Low latency</div>
                <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">Signals stream in milliseconds.</div>
              </div>
              <div className="rounded-2xl border border-black/10 bg-white/70 p-4 backdrop-blur dark:border-white/10 dark:bg-black/30">
                <div className="text-sm font-medium">Local security</div>
                <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">Keys stay encrypted on your PC.</div>
              </div>
              <div className="rounded-2xl border border-black/10 bg-white/70 p-4 backdrop-blur dark:border-white/10 dark:bg-black/30">
                <div className="text-sm font-medium">Access control</div>
                <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-300">Subscription-gated with RLS.</div>
              </div>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-3xl border border-black/10 bg-zinc-50 p-6 shadow-sm dark:border-white/10 dark:bg-zinc-950">
            <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-zinc-900/10 blur-3xl dark:bg-zinc-50/10" />
            <div className="relative">
              <div className="text-sm font-medium">How it works</div>
              <div className="mt-4 grid gap-3 text-sm text-zinc-700 dark:text-zinc-300">
                <div className="rounded-2xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                  <div className="font-medium">1) Sign in</div>
                  <div className="mt-1 text-zinc-600 dark:text-zinc-400">Supabase Auth (email/password or Google).</div>
                </div>
                <div className="rounded-2xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                  <div className="font-medium">2) Subscribe</div>
                  <div className="mt-1 text-zinc-600 dark:text-zinc-400">Unlock signal access + desktop downloads.</div>
                </div>
                <div className="rounded-2xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-black">
                  <div className="font-medium">3) Run the executor</div>
                  <div className="mt-1 text-zinc-600 dark:text-zinc-400">
                    Connect using your license key. Execution happens locally.
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-black/10 bg-white p-4 text-xs text-zinc-600 dark:border-white/10 dark:bg-black dark:text-zinc-300">
                <div className="font-mono">
                  HELLO → WELCOME → PING/PONG
                  <br />
                  SIGNAL(payload) → local execution
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
