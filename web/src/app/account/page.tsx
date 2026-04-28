import Link from "next/link";
import { redirect } from "next/navigation";

import { getMySubscription, isActiveSubscription } from "@/lib/subscription";

export default async function AccountPage() {
  const { user, subscription } = await getMySubscription();
  if (!user) redirect("/login");

  const active = isActiveSubscription(subscription);
  const stripeConfigured = Boolean(process.env.STRIPE_SECRET_KEY && process.env.STRIPE_PRICE_ID);

  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <main className="w-full max-w-2xl rounded-2xl border border-black/10 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-zinc-950">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Account</h1>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">{user.email}</div>
          </div>
          <form action="/logout" method="post">
            <button className="inline-flex h-10 items-center justify-center rounded-xl border border-black/10 px-4 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900">
              Log out
            </button>
          </form>
        </div>

        <div className="mt-8 grid gap-3 rounded-xl border border-black/10 bg-zinc-50 p-4 text-sm text-zinc-800 dark:border-white/10 dark:bg-zinc-900/40 dark:text-zinc-200">
          <div className="flex items-center justify-between gap-3">
            <div className="font-medium">Subscription</div>
            <div className={active ? "text-green-700 dark:text-green-300" : "text-red-700 dark:text-red-300"}>
              {active ? "Active" : "Not active"}
            </div>
          </div>
          <div className="flex items-center justify-between gap-3">
            <div className="text-zinc-600 dark:text-zinc-400">Status value</div>
            <div>{subscription?.status ?? "none"}</div>
          </div>
          <div className="flex items-center justify-between gap-3">
            <div className="text-zinc-600 dark:text-zinc-400">Current period end</div>
            <div>{subscription?.current_period_end ?? "—"}</div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          {stripeConfigured ? (
            <>
              <form action="/api/stripe/checkout" method="post">
                <button className="inline-flex h-11 w-full items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200 sm:w-auto">
                  Subscribe
                </button>
              </form>
              <form action="/api/stripe/portal" method="post">
                <button className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900 sm:w-auto">
                  Manage billing
                </button>
              </form>
            </>
          ) : (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
              Stripe is not configured yet. Subscription activation will be enabled once Stripe keys are set.
            </div>
          )}
          <Link
            href="/download"
            className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
          >
            Download desktop app
          </Link>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
          >
            Home
          </Link>
        </div>
      </main>
    </div>
  );
}

