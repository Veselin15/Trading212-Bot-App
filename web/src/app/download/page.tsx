import { redirect } from "next/navigation";

import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Container } from "@/components/ui/Container";

export default async function DownloadPage() {
  const { user, subscription } = await getMySubscription();
  if (!user) redirect("/login");

  const active = canUseProFeatures(subscription);
  if (!active) redirect("/dashboard");

  const downloadUrl = process.env.DESKTOP_DOWNLOAD_URL || "";
  const version = process.env.DESKTOP_APP_VERSION || "";
  const changelogUrl = process.env.DESKTOP_CHANGELOG_URL || "";
  const signalServer = process.env.DESKTOP_SIGNAL_SERVER_URL || "";

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <Container>
        <div className="mx-auto w-full max-w-2xl space-y-6">
          {/* Download card */}
          <Card className="p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
              Download SwiftTrade
            </h1>
            <p className="mt-2 text-sm text-slate-300">
              Your subscription is active. Download the desktop executor and start receiving live signals.
            </p>

            {/* Build info */}
            <div className="mt-6 rounded-2xl border border-white/10 bg-[#0A0A0A] p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Version</span>
                <span>{version || "latest"}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-slate-400">Platform</span>
                <span>Windows 10 / 11</span>
              </div>
              {signalServer && (
                <div className="mt-2 flex items-center justify-between gap-3">
                  <span className="text-slate-400">Signal server</span>
                  <span className="font-mono text-xs text-slate-300">{signalServer}</span>
                </div>
              )}
            </div>

            {/* Download buttons */}
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              {downloadUrl ? (
                <a
                  href={downloadUrl}
                  className="inline-flex h-11 items-center justify-center rounded-xl bg-emerald-500 px-5 text-sm font-medium text-slate-950 shadow-sm shadow-emerald-500/20 transition-colors hover:bg-[#00E676] focus:outline-none focus:ring-2 focus:ring-emerald-400/60"
                >
                  Download SwiftTrade.exe
                </a>
              ) : (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                  Download not yet available. Set{" "}
                  <code className="font-mono">DESKTOP_DOWNLOAD_URL</code> to enable this page.
                </div>
              )}

              {changelogUrl && (
                <a
                  href={changelogUrl}
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-5 text-sm font-medium text-slate-50 backdrop-blur transition-colors hover:bg-white/10"
                >
                  Release notes
                </a>
              )}

              <ButtonLink href="/dashboard" variant="secondary" className="w-full sm:w-auto">
                Back to dashboard
              </ButtonLink>
            </div>
          </Card>

          {/* Setup instructions */}
          <Card className="p-8">
            <h2 className="text-lg font-semibold text-slate-50">Quick start</h2>
            <ol className="mt-4 space-y-4 text-sm text-slate-300">
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-bold text-emerald-400">
                  1
                </span>
                <span>
                  Download <strong className="text-slate-100">SwiftTrade.exe</strong> above and run
                  it — no installation needed. Windows may show a SmartScreen prompt; click{" "}
                  <em>More info → Run anyway</em>.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-bold text-emerald-400">
                  2
                </span>
                <span>
                  In the <strong className="text-slate-100">Setup</strong> tab, paste your license
                  key (shown on the{" "}
                  <a href="/dashboard" className="text-emerald-400 hover:underline">
                    Dashboard
                  </a>
                  ) and click <strong className="text-slate-100">Validate</strong>.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-bold text-emerald-400">
                  3
                </span>
                <span>
                  Add your <strong className="text-slate-100">Trading212 Practice API key</strong>{" "}
                  (Settings → API inside Trading212) and click{" "}
                  <strong className="text-slate-100">Save practice keys</strong>.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-bold text-emerald-400">
                  4
                </span>
                <span>
                  Click <strong className="text-slate-100">Connect</strong> in the top bar. The
                  status dot turns green when live signals are flowing. Trades run in{" "}
                  <strong className="text-slate-100">Paper</strong> mode by default — switch to{" "}
                  <strong className="text-slate-100">Live</strong> only when you are ready to place
                  real orders (Pro license required).
                </span>
              </li>
            </ol>
          </Card>
        </div>
      </Container>
    </main>
  );
}
