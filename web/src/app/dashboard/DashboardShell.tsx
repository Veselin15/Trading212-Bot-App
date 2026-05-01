"use client";

import { useMemo, useState } from "react";
import { Copy, Download, Eye, EyeOff, LogOut } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";

function formatDateForUi(iso: string) {
  const parsed = new Date(iso);
  if (!Number.isFinite(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

function maskLicenseKey(value: string) {
  return "•".repeat(Math.min(28, Math.max(12, value.length)));
}

function LicenseKeyManager({ licenseKey }: { licenseKey: string }) {
  const [revealed, setRevealed] = useState(false);

  const displayed = revealed ? licenseKey : maskLicenseKey(licenseKey);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(licenseKey);
      toast.success("License Key copied!");
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

        <Button
          type="button"
          variant="secondary"
          className="h-10 gap-2 border-rose-500/30 text-rose-200 hover:bg-rose-500/10"
          onClick={() => {
            // TODO: Wire to backend endpoint that revokes and regenerates a new license key.
            toast.message("Regenerate Key is not wired yet.");
          }}
        >
          Regenerate Key
        </Button>
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

export function DashboardShell({ userEmail }: { userEmail: string | null }) {
  const mockSubscription = useMemo(() => {
    // TODO: Replace with Stripe subscription state fetched from your backend/Supabase table.
    return {
      active: true,
      currentPeriodEndIso: new Date(Date.now() + 1000 * 60 * 60 * 24 * 23).toISOString(),
    };
  }, []);

  const mockLicenseKey = useMemo(() => {
    // TODO: Replace with license row fetched from your backend/Supabase table.
    return "sk_live_a7b9-99xx-4f2a-b3c1-1c8e0b8f3d2a";
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      {/* Welcome header */}
      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
            Welcome back, <span className="text-sky-400">{userEmail ?? "you@example.com"}</span>
          </h1>
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
        {/* Subscription status card */}
        <Card variant="solid" className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-slate-50">Subscription Status</h2>
              <p className="mt-1 text-sm text-slate-400">Your current plan and renewal date.</p>
            </div>
            <Badge
              className={
                mockSubscription.active
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-white/10 bg-white/5 text-slate-300"
              }
            >
              {mockSubscription.active ? "Active" : "Inactive"}
            </Badge>
          </div>

          <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">Current Period End</div>
            <div className="mt-1 text-sm text-slate-100">{formatDateForUi(mockSubscription.currentPeriodEndIso)}</div>
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button
              type="button"
              variant="secondary"
              className="h-11 w-full sm:w-auto"
              onClick={() => {
                // TODO: Link to Stripe Customer Portal (server action -> portal session -> redirect).
                toast.message("Manage Billing is not wired yet.");
              }}
            >
              Manage Billing
            </Button>
          </div>
        </Card>

        {/* Download center card */}
        <Card variant="accent" className="relative overflow-hidden p-6">
          <div className="pointer-events-none absolute -right-28 -top-24 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
          <div className="pointer-events-none absolute -left-28 -bottom-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative">
            <h2 className="text-base font-semibold text-slate-50">Desktop Execution Engine</h2>
            <p className="mt-1 text-sm text-slate-300/90">
              Download the Windows client to connect your Trading212 account securely. Keys are encrypted locally.
            </p>

            <div className="mt-6">
              <ButtonLink href="/download" className="h-11 w-full gap-2 bg-sky-500 text-slate-950 hover:bg-sky-400">
                <Download className="h-4 w-4" />
                Download App (.exe)
              </ButtonLink>
            </div>
          </div>
        </Card>

        {/* License key manager card */}
        <LicenseKeyManager licenseKey={mockLicenseKey} />

        {/* Placeholder / spacer card to keep the grid balanced on desktop */}
        <Card variant="solid" className="p-6">
          <h2 className="text-base font-semibold text-slate-50">What happens next</h2>
          <p className="mt-1 text-sm text-slate-400">
            In the next step, we will wire this dashboard to live Stripe subscription state and your real license key
            stored in Supabase.
          </p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/pricing" variant="secondary" className="h-11 w-full sm:w-auto">
              View pricing
            </ButtonLink>
            <ButtonLink href="/product" variant="ghost" className="h-11 w-full sm:w-auto">
              Learn about the architecture
            </ButtonLink>
          </div>
        </Card>

        {/* Quick setup guide (full width) */}
        <Card variant="solid" className="p-6 lg:col-span-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-50">Quick Setup Guide</h2>
              <p className="mt-1 text-sm text-slate-400">
                Follow these steps to get from signup to local execution without confusion.
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

