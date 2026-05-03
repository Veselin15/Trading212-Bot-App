"use client";

import { Suspense, useState } from "react";
import { Copy, CreditCard, Download, Eye, EyeOff, LogOut } from "lucide-react";
import { toast } from "sonner";

import type { SubscriptionRow } from "@/lib/subscription-model";
import {
  canCancelStripeSubscription,
  canUseProFeatures,
  isActiveSubscription,
  isPastDueWithGrace,
} from "@/lib/subscription-model";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";

import { DashboardUrlToasts } from "./DashboardUrlToasts";

function formatDateForUi(iso: string | null) {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (!Number.isFinite(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

function maskLicenseKey(value: string) {
  return "•".repeat(Math.min(28, Math.max(12, value.length)));
}

function subscriptionUi(sub: SubscriptionRow | null, planTier: "free" | "pro") {
  if (!sub) {
    return { badgeLabel: "Free", badgeActive: false, detail: "No paid plan yet." };
  }

  if (sub.status === "canceled") {
    return {
      badgeLabel: "Canceled",
      badgeActive: false,
      detail: sub.current_period_end
        ? `Subscription canceled in Stripe. Pro access is off. Last billing period reference: ${formatDateForUi(sub.current_period_end)}.`
        : "Subscription canceled in Stripe. Pro access is off.",
    };
  }

  if (sub.status === "past_due") {
    const grace = isPastDueWithGrace(sub);
    return {
      badgeLabel: "Past due",
      badgeActive: grace,
      detail: grace
        ? "Update payment in Manage billing. Limited access may remain until the period end."
        : "Subscription is not active.",
    };
  }

  if (isActiveSubscription(sub)) {
    if (sub.status === "trialing") {
      return {
        badgeLabel: "Trial",
        badgeActive: true,
        detail: planTier === "pro" ? "Pro · trial access is active." : "Trial access is active.",
      };
    }
    return {
      badgeLabel: "Active",
      badgeActive: true,
      detail: planTier === "pro" ? "Pro plan · subscription is active." : "Paid subscription is active.",
    };
  }

  if (sub.status === "unpaid") {
    return { badgeLabel: "Inactive", badgeActive: false, detail: "Subscription is not active." };
  }
  return {
    badgeLabel: sub.status.replace(/_/g, " "),
    badgeActive: false,
    detail: "Subscription is not active.",
  };
}

function LicenseKeyManager({ licenseKey }: { licenseKey: string }) {
  const [revealed, setRevealed] = useState(false);

  const displayed = revealed ? licenseKey : maskLicenseKey(licenseKey);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(licenseKey);
      toast.success("License key copied.");
    } catch {
      toast.error("Clipboard access was blocked. Please copy manually.");
    }
  }

  return (
    <Card variant="solid" className="p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-50">License Key Manager</h2>
          <p className="mt-1 text-sm text-slate-400">
            Paste this key into your Desktop App to authenticate with our realtime signal channel.
          </p>
        </div>

        <form action="/api/license/regenerate" method="post">
          <Button
            type="submit"
            variant="secondary"
            className="h-10 gap-2 border-rose-500/30 text-rose-200 hover:bg-rose-500/10"
          >
            Regenerate Key
          </Button>
        </form>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-white/10 bg-black/30 px-4 py-3">
          <span className="truncate font-mono text-sm text-slate-100">{displayed}</span>
          <button
            type="button"
            className="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide license key" : "Reveal license key"}
          >
            {revealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        <div className="flex gap-3">
          <Button type="button" variant="secondary" className="h-11 gap-2" onClick={onCopy}>
            <Copy className="h-4 w-4" />
            Copy
          </Button>
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        This license key is separate from your Trading212 API key. Your Trading212 API key should only ever be entered
        in the Desktop App.
      </p>
    </Card>
  );
}

export type DashboardShellProps = {
  userEmail: string | null;
  subscription: SubscriptionRow | null;
  licenseKey: string | null;
  planTier: "free" | "pro";
  stripeCheckoutEnabled: boolean;
  stripePortalEnabled: boolean;
};

export function DashboardShell({
  userEmail,
  subscription,
  licenseKey,
  planTier,
  stripeCheckoutEnabled,
  stripePortalEnabled,
}: DashboardShellProps) {
  const proFeatures = canUseProFeatures(subscription);
  const ui = subscriptionUi(subscription, planTier);
  const canUsePortal = Boolean(stripePortalEnabled && subscription?.stripe_customer_id);
  const canCancelSubscription = Boolean(
    canUsePortal && canCancelStripeSubscription(subscription),
  );
  const showUpgrade = !proFeatures && stripeCheckoutEnabled;
  const showBillingBlock = Boolean(
    showUpgrade ||
      canUsePortal ||
      (!stripeCheckoutEnabled && !proFeatures) ||
      (proFeatures && stripePortalEnabled && !subscription?.stripe_customer_id),
  );

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      <Suspense fallback={null}>
        <DashboardUrlToasts />
      </Suspense>

      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
              Welcome back, <span className="text-emerald-400">{userEmail ?? "you@example.com"}</span>
            </h1>
            {planTier === "pro" ? (
              <Badge className="border-emerald-500/45 bg-emerald-500/15 text-emerald-200">Pro</Badge>
            ) : (
              <Badge className="border-slate-600/80 bg-white/5 text-slate-300">Free</Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Manage your subscription and license key. Trading execution runs locally in the Desktop App.
          </p>
        </div>

        <form action="/logout" method="post">
          <Button type="submit" variant="secondary" className="h-11 gap-2">
            <LogOut className="h-4 w-4" />
            Log out
          </Button>
        </form>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card variant="solid" className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-slate-50">Subscription Status</h2>
              <p className="mt-1 text-sm text-slate-400">{ui.detail}</p>
            </div>
            <Badge
              className={
                ui.badgeActive
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-white/10 bg-white/5 text-slate-300"
              }
            >
              {ui.badgeLabel}
            </Badge>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">Plan</div>
              <div className="mt-1 text-sm font-medium text-slate-100">
                {planTier === "pro" ? "Pro Automation" : "Paper / Free"}
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">Current period end</div>
              <div className="mt-1 text-sm text-slate-100">
                {formatDateForUi(subscription?.current_period_end ?? null)}
              </div>
              {subscription?.status === "canceled" && subscription?.current_period_end ? (
                <p className="mt-2 text-xs text-slate-500">
                  From Stripe billing (not used for access while subscription is canceled).
                </p>
              ) : null}
            </div>
          </div>

          {showBillingBlock ? (
            <div className="mt-6 border-t border-white/10 pt-5">
              <div className="mb-3 flex items-center gap-2 text-slate-300">
                <CreditCard className="h-4 w-4 text-emerald-400" />
                <span className="text-sm font-medium text-slate-200">Billing &amp; plan</span>
              </div>
              <p className="mb-4 text-xs text-slate-500">
                Payments are processed by Stripe. In this portal, <span className="text-slate-400">canceled</span> means
                Pro features and license keys are turned off immediately; dates above are for your records.
              </p>

              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                {showUpgrade ? (
                  <form action="/api/stripe/checkout" method="post">
                    <Button type="submit" className="h-11 w-full sm:w-auto">
                      Upgrade to Pro
                    </Button>
                  </form>
                ) : null}

                {!stripeCheckoutEnabled && !proFeatures ? (
                  <p className="text-sm text-amber-200/90">
                    Billing is not configured on this environment (missing Stripe keys or price).
                  </p>
                ) : null}

                {canUsePortal ? (
                  <form action="/api/stripe/portal" method="post">
                    <Button type="submit" variant="secondary" className="h-11 w-full sm:w-auto">
                      Manage billing
                    </Button>
                  </form>
                ) : proFeatures && stripePortalEnabled && !subscription?.stripe_customer_id ? (
                  <p className="text-sm text-slate-400">
                    Billing portal will be available after checkout creates your customer.
                  </p>
                ) : null}

                {canCancelSubscription ? (
                  <form action="/api/stripe/portal/cancel" method="post">
                    <Button
                      type="submit"
                      variant="secondary"
                      className="h-11 w-full border-rose-500/35 text-rose-100 hover:bg-rose-500/10 sm:w-auto"
                    >
                      Cancel subscription
                    </Button>
                  </form>
                ) : null}
              </div>
            </div>
          ) : null}
        </Card>

        <Card variant="accent" className="relative overflow-hidden p-6">
          <div className="pointer-events-none absolute -right-28 -top-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />
          <div className="pointer-events-none absolute -left-28 -bottom-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative">
            <h2 className="text-base font-semibold text-slate-50">Desktop Execution Engine</h2>
            <p className="mt-1 text-sm text-slate-300/90">
              Download the Windows client to connect your Trading212 account securely. Keys are encrypted locally.
            </p>

            <div className="mt-6">
              {proFeatures ? (
                <ButtonLink href="/download" className="h-11 w-full gap-2 bg-emerald-500 text-slate-950 hover:bg-[#00E676]">
                  <Download className="h-4 w-4" />
                  Download App (.exe)
                </ButtonLink>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-slate-400">
                    An active Pro subscription is required to download the desktop executor.
                  </p>
                  {showUpgrade ? (
                    <form action="/api/stripe/checkout" method="post">
                      <Button type="submit" className="h-11 w-full gap-2">
                        <Download className="h-4 w-4" />
                        Upgrade to download
                      </Button>
                    </form>
                  ) : (
                    <ButtonLink href="/pricing" variant="secondary" className="h-11 w-full">
                      View pricing
                    </ButtonLink>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>

        {proFeatures && licenseKey ? (
          <LicenseKeyManager licenseKey={licenseKey} />
        ) : proFeatures && !licenseKey ? (
          <Card variant="solid" className="p-6">
            <h2 className="text-base font-semibold text-slate-50">License Key</h2>
            <p className="mt-1 text-sm text-slate-400">
              Generate a key for the desktop app. You can regenerate it anytime while your subscription is active.
            </p>
            <form action="/api/license/regenerate" method="post" className="mt-5">
              <Button type="submit" className="h-11">
                Generate license key
              </Button>
            </form>
          </Card>
        ) : !proFeatures && licenseKey ? (
          <Card variant="solid" className="p-6">
            <h2 className="text-base font-semibold text-slate-50">License Key</h2>
            <p className="mt-1 text-sm text-slate-400">
              Your subscription is not eligible for Pro. Any previous key has been invalidated. Subscribe again to
              receive a new license.
            </p>
            {showUpgrade ? (
              <form action="/api/stripe/checkout" method="post" className="mt-5">
                <Button type="submit" variant="secondary" className="h-11">
                  Upgrade to Pro
                </Button>
              </form>
            ) : (
              <ButtonLink href="/pricing" variant="secondary" className="mt-5 inline-flex h-11 items-center">
                View pricing
              </ButtonLink>
            )}
          </Card>
        ) : (
          <Card variant="solid" className="p-6">
            <h2 className="text-base font-semibold text-slate-50">License Key</h2>
            <p className="mt-1 text-sm text-slate-400">
              An active Pro subscription is required to create and manage a desktop license key.
            </p>
            {showUpgrade ? (
              <form action="/api/stripe/checkout" method="post" className="mt-5">
                <Button type="submit" variant="secondary" className="h-11">
                  Upgrade to Pro
                </Button>
              </form>
            ) : null}
          </Card>
        )}

        <Card variant="solid" className="p-6">
          <h2 className="text-base font-semibold text-slate-50">Resources</h2>
          <p className="mt-1 text-sm text-slate-400">Pricing and how the portal fits with the desktop executor.</p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/pricing" variant="secondary" className="h-11 w-full sm:w-auto">
              View pricing
            </ButtonLink>
            <ButtonLink href="/product" variant="ghost" className="h-11 w-full sm:w-auto">
              Architecture
            </ButtonLink>
          </div>
        </Card>

        <Card variant="solid" className="p-6 lg:col-span-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-50">Quick Setup Guide</h2>
              <p className="mt-1 text-sm text-slate-400">
                From signup to local execution: portal for account and billing, desktop for broker keys.
              </p>
            </div>
          </div>

          <ol className="mt-5 space-y-3 text-sm text-slate-200">
            <li>
              <span className="font-medium text-slate-50">1.</span> Download and install the Desktop Engine.
            </li>
            <li>
              <span className="font-medium text-slate-50">2.</span> Generate an API Key inside your Trading212 settings.
            </li>
            <li>
              <span className="font-medium text-slate-50">3.</span> Open the Desktop App, paste your Trading212 API Key
              (kept local) AND your License Key (from this dashboard).
            </li>
            <li>
              <span className="font-medium text-slate-50">4.</span> Keep the app running to receive live algorithmic
              signals.
            </li>
          </ol>

          <Alert className="mt-6">
            <span className="font-semibold">Security Notice:</span> We will never ask for your Trading212 API key on this
            website. Your funds remain 100% in your control.
          </Alert>
        </Card>
      </div>
    </main>
  );
}
