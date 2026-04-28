import { ButtonLink } from "@/components/Button";

export default function PricingPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-14">
      <div className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">Pricing</h1>
        <p className="text-zinc-600 dark:text-zinc-300">
          Stripe is not enabled yet. For now, access can be granted manually by setting your subscription row to
          <span className="font-mono"> status=active</span> in Supabase.
        </p>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Free</div>
          <div className="mt-2 text-3xl font-semibold">€0</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Explore the portal UI.</div>
          <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
            <li>Portal access</li>
            <li>No signal access</li>
          </ul>
          <div className="mt-6">
            <ButtonLink href="/login" variant="secondary" className="w-full">
              Login
            </ButtonLink>
          </div>
        </div>

        <div className="rounded-2xl border border-black/10 bg-zinc-50 p-6 shadow-sm dark:border-white/10 dark:bg-zinc-950">
          <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Pro</div>
          <div className="mt-2 text-3xl font-semibold">€?</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Realtime signals + desktop executor.</div>
          <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
            <li>Realtime signals (Supabase)</li>
            <li>Desktop download</li>
            <li>Account page</li>
          </ul>
          <div className="mt-6">
            <ButtonLink href="/account" className="w-full">
              Go to account
            </ButtonLink>
          </div>
        </div>

        <div className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
          <div className="text-sm font-medium text-zinc-600 dark:text-zinc-300">Enterprise</div>
          <div className="mt-2 text-3xl font-semibold">Talk to us</div>
          <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">Custom flows and onboarding.</div>
          <ul className="mt-6 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
            <li>Custom support</li>
            <li>Custom execution logic</li>
          </ul>
          <div className="mt-6">
            <a
              className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
              href="mailto:support@example.com"
            >
              Contact
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}

