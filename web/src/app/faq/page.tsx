export default function FaqPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-14">
      <h1 className="text-3xl font-semibold tracking-tight">FAQ</h1>
      <div className="mt-8 space-y-6">
        <div className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <div className="font-medium">How do signals reach the desktop app?</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
            Signals are inserted into the <span className="font-mono">signals</span> table in Supabase. Supabase Realtime
            pushes new rows to subscribed desktop clients instantly.
          </div>
        </div>
        <div className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <div className="font-medium">Where are my Trading212 keys stored?</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
            On your machine, encrypted locally. The web portal never needs your broker keys.
          </div>
        </div>
        <div className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <div className="font-medium">Why do I need an active subscription?</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
            Supabase RLS allows reading <span className="font-mono">signals</span> only when your subscription is active.
          </div>
        </div>
      </div>
    </main>
  );
}

