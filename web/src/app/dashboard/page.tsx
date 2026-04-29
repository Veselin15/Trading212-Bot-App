import { redirect } from "next/navigation";

import { getMySubscription, isActiveSubscription } from "@/lib/subscription";
import { getMyLicense } from "@/lib/license";
import { ButtonLink } from "@/components/ui/Button";
import { CopyToClipboardButton } from "@/components/ui/CopyToClipboardButton";

export default async function DashboardPage() {
  const { user, subscription } = await getMySubscription();
  if (!user) redirect("/login");

  const active = isActiveSubscription(subscription);
  const stripeConfigured = Boolean(process.env.STRIPE_SECRET_KEY && process.env.STRIPE_PRICE_ID);
  const { license } = await getMyLicense();

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-5xl space-y-8 rounded-2xl border border-slate-800/70 bg-slate-950/60 p-8 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Dashboard</h1>
            <p className="text-sm text-slate-300">
              Welcome back, <span className="font-medium text-slate-50">{user.email}</span>.
            </p>
          </div>
          <form action="/logout" method="post">
            <button className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-800/80 px-4 text-sm font-medium text-slate-50 hover:bg-white/5">
              Log out
            </button>
          </form>
        </div>

        {/* Subscription status */}
        <section className="grid gap-4 rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 text-sm text-slate-200 sm:grid-cols-3">
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Subscription</div>
            <div className="text-sm font-medium text-slate-50">
              {active ? "Active" : "Not active"}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Status value</div>
            <div>{subscription?.status ?? "none"}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Current period end</div>
            <div>{subscription?.current_period_end ?? "—"}</div>
          </div>
        </section>

        {/* License + download */}
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 text-sm text-slate-200">
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium text-slate-50">License key</div>
              {active ? (
                <form action="/api/license/regenerate" method="post">
                  <button className="inline-flex h-9 items-center justify-center rounded-xl border border-slate-800/80 px-3 text-xs font-medium text-slate-50 hover:bg-white/5">
                    Regenerate
                  </button>
                </form>
              ) : (
                <div className="text-xs text-slate-400">Requires active subscription</div>
              )}
            </div>

            {active ? (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/70 px-3 py-2 font-mono text-xs text-slate-100 sm:text-sm">
                  {license?.license_key ?? "Not generated yet"}
                </div>
                {license?.license_key ? <CopyToClipboardButton value={license.license_key} /> : null}
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                Subscribe to generate a desktop license key for the Trading212 executor.
              </p>
            )}

            <div className="pt-2 text-xs text-slate-400">
              The license key is used by the desktop app only. It never includes your Trading212 API key.
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 text-sm text-slate-200">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="font-medium text-slate-50">Desktop app</div>
                <p className="mt-1 text-xs text-slate-400">
                  Download the Windows executor and keep Trading212 keys encrypted on your machine.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/download" className="w-full sm:w-auto">
                Download Desktop Client (.exe)
              </ButtonLink>
              <ButtonLink href="/pricing" variant="secondary" className="w-full sm:w-auto">
                View plans
              </ButtonLink>
            </div>
          </div>
        </section>

        {/* Setup guide */}
        <section className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-950/70 p-4 text-sm text-slate-200">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-medium text-slate-50">Trading212 setup guide</div>
              <p className="mt-1 text-xs text-slate-400">
                Follow these steps to connect the executor. The web dashboard never asks for your Trading212 API key.
              </p>
            </div>
          </div>

          <ol className="mt-2 space-y-3 text-sm text-slate-200">
            <li>
              <span className="font-medium text-slate-50">1. Generate a Trading212 API key.</span>{" "}
              Log into your Trading212 account in the browser, open the API keys section, and create a new key with the
              minimal permissions required for your strategy.
            </li>
            <li>
              <span className="font-medium text-slate-50">2. Install and open the desktop app.</span>{" "}
              Download the Windows installer from the button above, run it, and launch the Trading212 Bot desktop
              client.
            </li>
            <li>
              <span className="font-medium text-slate-50">3. Paste the API key into the desktop app only.</span>{" "}
              When prompted, paste your Trading212 API key directly into the local desktop client. It is stored
              encrypted on your machine and never sent to this website or the backend.
            </li>
            <li>
              <span className="font-medium text-slate-50">4. Enter your license key in the desktop app.</span>{" "}
              Copy the license key from above and paste it into the desktop app so it can subscribe to your Supabase
              signals.
            </li>
            <li>
              <span className="font-medium text-slate-50">5. Confirm you see live heartbeats.</span>{" "}
              The app will show PING/PONG heartbeats and live signal status once connected. Execution remains fully
              local on your device.
            </li>
          </ol>

          <div className="mt-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200">
            For security: never paste your Trading212 API key into the browser or share it over chat/email. Only the
            desktop app should ever see it.
          </div>
        </section>

        {/* Billing actions */}
        <section className="flex flex-col gap-3 border-t border-slate-800/70 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-slate-400">
            Manage your subscription and billing details at any time.
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {stripeConfigured ? (
              <>
                <form action="/api/stripe/checkout" method="post">
                  <button className="inline-flex h-10 w-full items-center justify-center rounded-xl bg-sky-500 px-4 text-sm font-medium text-slate-950 hover:bg-sky-400 sm:w-auto">
                    Upgrade to Pro
                  </button>
                </form>
                <form action="/api/stripe/portal" method="post">
                  <button className="inline-flex h-10 w-full items-center justify-center rounded-xl border border-slate-800/80 px-4 text-sm font-medium text-slate-50 hover:bg-white/5 sm:w-auto">
                    Manage billing
                  </button>
                </form>
              </>
            ) : (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-100">
                Stripe is not configured yet. Subscription activation will be enabled once Stripe keys are set in the
                environment.
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

