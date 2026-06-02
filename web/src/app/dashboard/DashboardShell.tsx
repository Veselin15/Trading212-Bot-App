"use client";

import { Suspense, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Copy,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  Key,
  LogOut,
  RefreshCw,
  Shield,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import type { SubscriptionRow } from "@/lib/subscription-model";
import {
  canCancelStripeSubscription,
  isActiveSubscription,
  isPastDueWithGrace,
} from "@/lib/subscription-model";
import type { EffectiveTier } from "@/lib/tier";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

import { DashboardUrlToasts } from "./DashboardUrlToasts";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

function maskKey(value: string) {
  return "•".repeat(Math.min(28, Math.max(12, value.length)));
}

function subscriptionUi(sub: SubscriptionRow | null, effectiveTier: EffectiveTier, trialDaysLeft: number | null) {
  const isPro = effectiveTier === "PRO";

  if (!isPro) {
    if (effectiveTier === "TRIAL") {
      const days = trialDaysLeft ?? 0;
      return {
        badgeLabel: "Trial",
        badgeActive: true,
        detail: `Free trial — ${days} day${days === 1 ? "" : "s"} left. Paper trading only; upgrade to unlock live execution.`,
      };
    }
    // EXPIRED
    if (sub?.status === "canceled") {
      return {
        badgeLabel: "Expired",
        badgeActive: false,
        detail: sub.current_period_end
          ? `Subscription canceled. Last period: ${formatDate(sub.current_period_end)}. Upgrade to resume.`
          : "Subscription canceled. Upgrade to resume.",
      };
    }
    if (sub?.status === "past_due") {
      return {
        badgeLabel: "Past due",
        badgeActive: false,
        detail: "Payment failed — update your card in Manage billing to restore access.",
      };
    }
    return { badgeLabel: "Expired", badgeActive: false, detail: "Your free trial has ended. Upgrade to resume." };
  }

  // PRO
  if (sub && isPastDueWithGrace(sub)) {
    return {
      badgeLabel: "Past due",
      badgeActive: true,
      detail: "Update payment in Manage billing. Pro access remains until the period end.",
    };
  }
  if (sub && isActiveSubscription(sub) && sub.status === "trialing") {
    return { badgeLabel: "Active", badgeActive: true, detail: "Pro · trial access is active." };
  }
  return { badgeLabel: "Active", badgeActive: true, detail: "Pro plan · active." };
}

function LicenseKeyManager({ licenseKey }: { licenseKey: string }) {
  const [revealed, setRevealed] = useState(false);
  const displayed = revealed ? licenseKey : maskKey(licenseKey);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(licenseKey);
      toast.success("License key copied.");
    } catch {
      toast.error("Clipboard access was blocked. Please copy manually.");
    }
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-emerald-500/25 bg-[#07090d] p-6 shadow-[0_0_40px_-16px_rgba(0,230,118,0.22)]">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-emerald-500/8 blur-3xl" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-500/35 to-transparent" />

      <div className="relative">
        {/* Header */}
        <div className="mb-5 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10">
              <Key className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <p className="font-semibold text-slate-50">License Key</p>
              <p className="mt-0.5 text-xs text-slate-500">Paste into the Desktop App to activate live signals</p>
            </div>
          </div>
          <form action="/api/license/regenerate" method="post">
            <Button
              type="submit"
              variant="secondary"
              className="h-9 gap-1.5 border-rose-500/25 text-xs text-rose-300/90 hover:border-rose-500/40 hover:bg-rose-500/10"
            >
              <RefreshCw className="h-3 w-3" />
              Regenerate
            </Button>
          </form>
        </div>

        {/* Key display */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-2 rounded-2xl border border-white/[0.08] bg-black/40 px-4 py-3">
            <span className="truncate font-mono text-sm text-slate-100">{displayed}</span>
            <button
              type="button"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] text-slate-400 transition-all hover:bg-white/[0.08] hover:text-slate-200"
              onClick={() => setRevealed((v) => !v)}
              aria-label={revealed ? "Hide key" : "Reveal key"}
            >
              {revealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <Button type="button" variant="secondary" className="h-11 shrink-0 gap-2" onClick={onCopy}>
            <Copy className="h-4 w-4" />
            Copy
          </Button>
        </div>

        <p className="mt-4 text-xs text-slate-700">
          Separate from your Trading212 API key. Your Trading212 API key should only be entered in the Desktop App.
        </p>
      </div>
    </div>
  );
}

export type DashboardShellProps = {
  userEmail: string | null;
  subscription: SubscriptionRow | null;
  licenseKey: string | null;
  effectiveTier: EffectiveTier;
  trialDaysLeft: number | null;
  stripeCheckoutEnabled: boolean;
  stripePortalEnabled: boolean;
  schemaSetupMessage?: string | null;
};

export function DashboardShell({
  userEmail,
  subscription,
  licenseKey,
  effectiveTier,
  trialDaysLeft,
  stripeCheckoutEnabled,
  stripePortalEnabled,
  schemaSetupMessage,
}: DashboardShellProps) {
  const proFeatures = effectiveTier === "PRO";
  const isTrial = effectiveTier === "TRIAL";
  const isExpired = effectiveTier === "EXPIRED";
  const canUseLicense = !isExpired; // TRIAL + PRO may hold a license key
  const planLabel = proFeatures ? "Pro Automation" : isTrial ? "Trial (paper)" : "Expired";
  const ui = subscriptionUi(subscription, effectiveTier, trialDaysLeft);
  const canUsePortal = Boolean(stripePortalEnabled && subscription?.stripe_customer_id);
  const canCancelSubscription = Boolean(canUsePortal && canCancelStripeSubscription(subscription));
  const showUpgrade = !proFeatures && stripeCheckoutEnabled;
  const showBillingBlock = Boolean(
    showUpgrade || canUsePortal ||
    (!stripeCheckoutEnabled && !proFeatures) ||
    (proFeatures && stripePortalEnabled && !subscription?.stripe_customer_id),
  );

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      <Suspense fallback={null}>
        <DashboardUrlToasts />
      </Suspense>

      {schemaSetupMessage && (
        <Alert className="mb-6 border-amber-500/30 bg-amber-500/10 text-amber-100">
          <span className="font-semibold">Setup required:</span> {schemaSetupMessage}
        </Alert>
      )}

      {isTrial && (
        <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.07] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Activity className="h-4 w-4 shrink-0 text-emerald-400" />
            <p className="text-sm text-slate-200">
              <span className="font-semibold text-emerald-300">
                {(trialDaysLeft ?? 0) === 1 ? "1 day" : `${trialDaysLeft ?? 0} days`} left in your free trial.
              </span>{" "}
              Paper-trade the algorithm now — upgrade to unlock live execution.
            </p>
          </div>
          {showUpgrade && (
            <form action="/api/stripe/checkout" method="post" className="shrink-0">
              <Button type="submit" className="h-10 gap-2 w-full sm:w-auto">
                Upgrade to Live Execution <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
          )}
        </div>
      )}

      {isExpired && (
        <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/[0.07] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-4 w-4 shrink-0 text-rose-400" />
            <p className="text-sm text-slate-200">
              <span className="font-semibold text-rose-300">Your free trial has ended.</span>{" "}
              The algorithm is paused. Upgrade to resume paper and live trading.
            </p>
          </div>
          {showUpgrade && (
            <form action="/api/stripe/checkout" method="post" className="shrink-0">
              <Button type="submit" className="h-10 gap-2 w-full sm:w-auto">
                Upgrade now <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
          )}
        </div>
      )}

      {/* ── Top header ── */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
              Welcome back,{" "}
              <span className="text-gradient-brand">{userEmail ?? "you@example.com"}</span>
            </h1>
            {proFeatures ? (
              <Badge className="border-emerald-500/45 bg-emerald-500/15 text-emerald-200">Pro</Badge>
            ) : isTrial ? (
              <Badge className="border-emerald-500/35 bg-emerald-500/10 text-emerald-300">Trial</Badge>
            ) : (
              <Badge className="border-rose-500/40 bg-rose-500/10 text-rose-300">Expired</Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Manage your subscription and license key. Trading execution runs locally in the Desktop App.
          </p>
        </div>
        <form action="/logout" method="post">
          <Button type="submit" variant="secondary" className="h-10 gap-2">
            <LogOut className="h-4 w-4" /> Log out
          </Button>
        </form>
      </div>

      {/* ── Status chips ── */}
      <div className="mb-8 flex flex-wrap gap-2.5">
        <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3.5 py-1.5">
          <Activity className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-xs text-slate-500">Status:</span>
          <span className={`text-xs font-semibold ${ui.badgeActive ? "text-emerald-400" : "text-slate-400"}`}>
            {ui.badgeLabel}
          </span>
          {ui.badgeActive && (
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3.5 py-1.5">
          <Shield className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-xs text-slate-500">Plan:</span>
          <span className="text-xs font-semibold text-slate-300">{planLabel}</span>
        </div>
        {subscription?.current_period_end && proFeatures && (
          <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3.5 py-1.5">
            <span className="text-xs text-slate-500">Renews:</span>
            <span className="font-mono text-xs text-slate-400">{formatDate(subscription.current_period_end)}</span>
          </div>
        )}
      </div>

      {/* ── Main grid ── */}
      <div className="grid gap-5 lg:grid-cols-2">

        {/* Subscription status */}
        <Card variant="solid" className="p-6">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold text-slate-50">Subscription Status</p>
              <p className="mt-1 text-sm text-slate-500">{ui.detail}</p>
            </div>
            <Badge className={ui.badgeActive
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "border-white/[0.08] bg-white/[0.04] text-slate-400"}>
              {ui.badgeLabel}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/[0.07] bg-black/20 px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-600">Plan</p>
              <p className="mt-1.5 text-sm font-semibold text-slate-200">{planLabel}</p>
            </div>
            <div className="rounded-2xl border border-white/[0.07] bg-black/20 px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-600">Period end</p>
              <p className="mt-1.5 font-mono text-sm text-slate-200">
                {formatDate(subscription?.current_period_end ?? null)}
              </p>
            </div>
          </div>

          {showBillingBlock && (
            <div className="mt-5 border-t border-white/[0.07] pt-5">
              <div className="mb-3 flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-emerald-400/70" />
                <span className="text-sm font-medium text-slate-300">Billing &amp; plan</span>
              </div>
              <p className="mb-4 text-xs leading-relaxed text-slate-600">
                Payments via Stripe. Cancellation immediately turns off Pro features and license keys.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                {showUpgrade && (
                  <form action="/api/stripe/checkout" method="post">
                    <Button type="submit" className="h-10 gap-2 w-full sm:w-auto">
                      Upgrade to Pro <ArrowRight className="h-4 w-4" />
                    </Button>
                  </form>
                )}
                {!stripeCheckoutEnabled && !proFeatures && (
                  <p className="text-sm text-amber-300/80">Billing not configured (missing Stripe keys).</p>
                )}
                {canUsePortal && (
                  <form action="/api/stripe/portal" method="post">
                    <Button type="submit" variant="secondary" className="h-10 w-full sm:w-auto">Manage billing</Button>
                  </form>
                )}
                {proFeatures && stripePortalEnabled && !subscription?.stripe_customer_id && (
                  <p className="text-sm text-slate-500">Billing portal available after checkout creates your customer.</p>
                )}
                {canCancelSubscription && (
                  <form action="/api/stripe/portal/cancel" method="post">
                    <Button type="submit" variant="secondary" className="h-10 w-full border-rose-500/30 text-rose-300/90 hover:bg-rose-500/10 sm:w-auto">
                      Cancel subscription
                    </Button>
                  </form>
                )}
              </div>
            </div>
          )}
        </Card>

        {/* Desktop executor */}
        <Card variant="accent" className="relative overflow-hidden p-6">
          <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-emerald-500/12 blur-3xl" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/30 to-transparent" />
          <div className="relative">
            <div className="mb-1 flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-400" strokeWidth={1.75} />
              <p className="font-semibold text-slate-50">Desktop Execution Engine</p>
            </div>
            <p className="mb-6 mt-1 text-sm text-slate-400">
              Download the Windows client to connect your Trading212 account. API keys are encrypted and stored locally.
            </p>
            <div className="space-y-3">
              <ButtonLink href="/download" className="h-11 w-full gap-2">
                <Download className="h-4 w-4" /> Download App (.exe)
              </ButtonLink>
              {isTrial && (
                <p className="text-xs text-slate-500">Trial: paper-trade the algorithm on your practice account. Upgrade to unlock real-money automation.</p>
              )}
              {isExpired && (
                <p className="text-xs text-rose-300/80">Trial ended — upgrade to resume paper and live trading.</p>
              )}
            </div>
          </div>
        </Card>

        {/* License key area */}
        {canUseLicense && licenseKey ? (
          <LicenseKeyManager licenseKey={licenseKey} />
        ) : canUseLicense && !licenseKey ? (
          <Card variant="solid" className="p-6">
            <div className="mb-1 flex items-center gap-2">
              <Key className="h-4 w-4 text-emerald-400/70" strokeWidth={1.75} />
              <p className="font-semibold text-slate-50">License Key</p>
            </div>
            <p className="mb-5 mt-1 text-sm text-slate-500">
              {isTrial
                ? "Generate a key for the desktop app to paper-trade during your trial."
                : "Generate a key for the desktop app. Regenerate at any time while subscribed."}
            </p>
            <form action="/api/license/regenerate" method="post">
              <Button type="submit" className="h-11">Generate license key</Button>
            </form>
          </Card>
        ) : (
          <Card variant="solid" className="p-6">
            <p className="font-semibold text-slate-50">License Key</p>
            <p className="mt-1 mb-5 text-sm text-slate-500">
              {licenseKey
                ? "Your free trial has ended, so this key is inactive. Upgrade to reactivate the desktop app."
                : "Your free trial has ended. Upgrade to issue a license key and resume the desktop app."}
            </p>
            {showUpgrade ? (
              <form action="/api/stripe/checkout" method="post">
                <Button type="submit" variant="secondary" className="h-11">Upgrade now</Button>
              </form>
            ) : (
              <ButtonLink href="/pricing" variant="secondary" className="inline-flex h-11 items-center">View pricing</ButtonLink>
            )}
          </Card>
        )}

        {/* Resources */}
        <Card variant="solid" className="p-6">
          <p className="font-semibold text-slate-50">Resources</p>
          <p className="mt-1 mb-5 text-sm text-slate-500">Learn how the portal and desktop executor fit together.</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/pricing" variant="secondary" className="h-11 w-full sm:w-auto">View pricing</ButtonLink>
            <ButtonLink href="/product" variant="ghost" className="h-11 w-full sm:w-auto">Architecture</ButtonLink>
          </div>
        </Card>

        {/* Quick setup */}
        <div className="relative overflow-hidden rounded-3xl border border-white/[0.07] bg-[#07070b] p-6 lg:col-span-2">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />

          <div className="mb-6">
            <p className="font-semibold text-slate-50">Quick Setup Guide</p>
            <p className="mt-1 text-sm text-slate-500">From signup to local execution in under 10 minutes.</p>
          </div>

          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { n: "1", text: "Download and install the Desktop Engine." },
              { n: "2", text: "Generate an API Key inside your Trading212 account settings." },
              { n: "3", text: "Open the Desktop App — paste your Trading212 API Key (local only) and your License Key (from this dashboard)." },
              { n: "4", text: "Keep the app running to receive live algorithmic signals and auto-execute trades." },
            ].map((step) => (
              <div key={step.n} className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="mb-3 flex h-7 w-7 items-center justify-center rounded-full border border-emerald-500/25 bg-emerald-500/10">
                  <span className="font-mono text-xs font-bold text-emerald-400">{step.n}</span>
                </div>
                <p className="text-sm leading-relaxed text-slate-300">{step.text}</p>
              </div>
            ))}
          </ol>

          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.05] p-4">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400/70" />
            <p className="text-sm text-slate-400">
              <span className="font-semibold text-emerald-300">Security notice: </span>
              We will never ask for your Trading212 API key on this website. Your funds remain 100% in your control.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
