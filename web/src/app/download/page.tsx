import { redirect } from "next/navigation";

import { getMySubscription, isActiveSubscription } from "@/lib/subscription";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Container } from "@/components/ui/Container";

export default async function DownloadPage() {
  const { user, subscription } = await getMySubscription();
  if (!user) redirect("/login");

  const active = isActiveSubscription(subscription);
  if (!active) redirect("/dashboard");

  const downloadUrl = process.env.DESKTOP_DOWNLOAD_URL || "";
  const version = process.env.DESKTOP_APP_VERSION || "";
  const changelogUrl = process.env.DESKTOP_CHANGELOG_URL || "";

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <Container>
        <div className="mx-auto w-full max-w-2xl">
          <Card className="p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Download</h1>
            <p className="mt-2 text-sm text-slate-300">
              Your subscription is active. Download the latest desktop executor below.
            </p>

            <div className="mt-6 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between gap-3">
                <div className="text-slate-400">Version</div>
                <div>{version || "latest"}</div>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div className="text-slate-400">Platform</div>
                <div>Windows</div>
              </div>
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              {downloadUrl ? (
                <a
                  href={downloadUrl}
                  className="inline-flex h-11 items-center justify-center rounded-xl bg-sky-500 px-5 text-sm font-medium text-slate-950 shadow-sm shadow-sky-500/20 transition-colors hover:bg-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/60"
                >
                  Download installer
                </a>
              ) : (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                  Download URL is not configured. Set <code className="font-mono">DESKTOP_DOWNLOAD_URL</code>.
                </div>
              )}

              {changelogUrl ? (
                <a
                  href={changelogUrl}
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-800/90 bg-white/5 px-5 text-sm font-medium text-slate-50 backdrop-blur transition-colors hover:bg-white/10"
                >
                  Release notes
                </a>
              ) : null}

              <ButtonLink href="/dashboard" variant="secondary" className="w-full sm:w-auto">
                Back to dashboard
              </ButtonLink>
            </div>
          </Card>
        </div>
      </Container>
    </main>
  );
}

