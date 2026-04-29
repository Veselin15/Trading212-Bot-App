export default function FaqPage() {
  return (
    <main>
      <div className="mx-auto w-full max-w-3xl px-6 py-14 sm:py-16">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">FAQ</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          The short version: the web coordinates access and licensing; the desktop app executes locally.
        </p>

        <div className="mt-10 space-y-4">
          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">How do signals reach the desktop app?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              Signals are inserted into the <span className="font-mono text-slate-200">signals</span> table in Supabase.
              Supabase Realtime pushes new rows to subscribed desktop clients.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">Where are my Trading212 keys stored?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              On your machine, encrypted locally. The web portal never asks for or stores your broker keys.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">Why do I need an active subscription?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              Supabase RLS allows reading <span className="font-mono text-slate-200">signals</span> only when your
              subscription is active. This gates the feed without exposing broker credentials.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">Is this “hands-off” fully automated trading?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              In Pro, yes — the desktop app can auto-execute orders when a signal arrives. You can also run in paper /
              monitoring mode first.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">What markets does it support?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              The current strategy focuses on European stocks (as available via Trading212). Exact universe can evolve as
              liquidity and execution constraints change.
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur">
            <div className="font-medium text-slate-50">Do you guarantee returns?</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">
              No. Trading is risky. Backtests can be misleading and do not guarantee future results.
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

