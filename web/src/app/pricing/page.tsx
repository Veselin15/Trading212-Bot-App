import { ButtonLink } from "@/components/ui/Button";

export default function PricingPage() {
  return (
    <main className="relative">
      <div className="pointer-events-none absolute inset-x-0 -top-24 -z-10 h-[22rem] bg-[radial-gradient(60%_60%_at_50%_0%,rgba(24,24,27,0.12),transparent_65%)] dark:bg-[radial-gradient(60%_60%_at_50%_0%,rgba(244,244,245,0.10),transparent_65%)]" />

      <div className="mx-auto w-full max-w-6xl px-6 py-16 sm:py-20">
        <div className="flex flex-col gap-3">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Pricing</h1>
          <p className="max-w-2xl text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            Simple access: the portal + your license key. Stripe can be enabled when you’re ready—until then, you can
            grant access by setting your subscription row to <span className="font-mono">status=active</span> in Supabase.
          </p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          <div className="rounded-3xl border border-black/10 bg-white/70 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-black/30">
            <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Free</div>
            <div className="mt-2 text-4xl font-semibold tracking-tight">€0</div>
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Try the portal and explore the flow.</div>
            <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
              <li>Portal access</li>
              <li>Account page</li>
              <li>Desktop download page (gated)</li>
            </ul>
            <div className="mt-6">
              <ButtonLink href="/login" variant="secondary" className="w-full">
                Login
              </ButtonLink>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-3xl border border-black/10 bg-zinc-50 p-6 shadow-sm dark:border-white/10 dark:bg-zinc-950">
            <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-zinc-900/10 blur-3xl dark:bg-zinc-50/10" />
            <div className="relative">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Pro</div>
                <div className="rounded-full border border-black/10 bg-white px-2 py-1 text-xs text-zinc-700 dark:border-white/10 dark:bg-black dark:text-zinc-300">
                  Most popular
                </div>
              </div>
              <div className="mt-2 text-4xl font-semibold tracking-tight">€?</div>
              <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Realtime signals + desktop executor.</div>
              <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
                <li>Signals feed (RLS gated)</li>
                <li>License key for executor</li>
                <li>Download access</li>
              </ul>
              <div className="mt-6">
                <ButtonLink href="/dashboard" className="w-full">
                  Go to dashboard
                </ButtonLink>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-black/10 bg-white/70 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-black/30">
            <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Enterprise</div>
            <div className="mt-2 text-2xl font-semibold tracking-tight">Custom onboarding</div>
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
              Dedicated support, custom execution logic, and tailored access controls.
            </div>
            <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
              <li>Priority support</li>
              <li>Custom broker connectors</li>
              <li>Custom compliance constraints</li>
            </ul>
            <div className="mt-6">
              <a
                className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-black/10 bg-white/60 px-5 text-sm font-medium text-zinc-950 backdrop-blur hover:bg-white dark:border-white/10 dark:bg-black/30 dark:text-zinc-50 dark:hover:bg-black/50"
                href="mailto:support@example.com"
              >
                Contact
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

