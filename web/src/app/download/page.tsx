import Link from "next/link";
import { redirect } from "next/navigation";

import { getMySubscription, isActiveSubscription } from "@/lib/subscription";

export default async function DownloadPage() {
  const { user, subscription } = await getMySubscription();
  if (!user) redirect("/login");

  const active = isActiveSubscription(subscription);
  if (!active) redirect("/account");

  const downloadUrl = process.env.DESKTOP_DOWNLOAD_URL || "";
  const version = process.env.DESKTOP_APP_VERSION || "";
  const changelogUrl = process.env.DESKTOP_CHANGELOG_URL || "";

  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <main className="w-full max-w-2xl rounded-2xl border border-black/10 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-zinc-950">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Download</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Your subscription is active. Download the latest desktop executor below.
        </p>

        <div className="mt-6 rounded-xl border border-black/10 bg-zinc-50 p-4 text-sm text-zinc-800 dark:border-white/10 dark:bg-zinc-900/40 dark:text-zinc-200">
          <div className="flex items-center justify-between gap-3">
            <div className="text-zinc-600 dark:text-zinc-400">Version</div>
            <div>{version || "latest"}</div>
          </div>
          <div className="mt-2 flex items-center justify-between gap-3">
            <div className="text-zinc-600 dark:text-zinc-400">Platform</div>
            <div>Windows</div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          {downloadUrl ? (
            <a
              href={downloadUrl}
              className="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
            >
              Download installer
            </a>
          ) : (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
              Download URL is not configured. Set <code className="font-mono">DESKTOP_DOWNLOAD_URL</code>.
            </div>
          )}

          {changelogUrl ? (
            <a
              href={changelogUrl}
              className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
            >
              Release notes
            </a>
          ) : null}

          <Link
            href="/account"
            className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
          >
            Back to account
          </Link>
        </div>
      </main>
    </div>
  );
}

