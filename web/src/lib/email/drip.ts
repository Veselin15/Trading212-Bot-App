import type { AdminClient } from "@/lib/billing-license-sync";
import { sendEmail, type SendEmailResult } from "@/lib/email/resend";

/** Trial drip stages (Phase 5). Each maps to an idempotency column on `public.profiles`. */
export type DripKind = "welcome" | "day7" | "day13" | "expired";

const DRIP_COLUMN: Record<DripKind, string> = {
  welcome: "welcome_email_sent_at",
  day7: "day7_email_sent_at",
  day13: "day13_email_sent_at",
  expired: "expired_email_sent_at",
};

function siteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app").replace(/\/$/, "");
}

function template(kind: DripKind, daysLeft: number | null): { subject: string; html: string } {
  const site = siteUrl();
  const upgrade = `${site}/pricing`;
  const dash = `${site}/dashboard`;
  const wrap = (body: string) =>
    `<div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;color:#0f172a">${body}</div>`;

  switch (kind) {
    case "welcome":
      return {
        subject: "Welcome to SwiftTrade — connect your Trading212 demo account",
        html: wrap(
          `<h2>Welcome to SwiftTrade</h2>
           <p>Your 14-day free trial is live. Download the desktop app, paste your license key
           from your <a href="${dash}">dashboard</a>, and connect your Trading212 <b>practice</b> account
           to start paper-trading the algorithm today.</p>
           <p><a href="${dash}">Open your dashboard →</a></p>`,
        ),
      };
    case "day7":
      return {
        subject: "Halfway through your trial — see what the algorithm did this week",
        html: wrap(
          `<h2>One week in</h2>
           <p>You're halfway through your free trial${daysLeft != null ? ` (${daysLeft} days left)` : ""}.
           Review this week's signals and paper-trading results on your <a href="${dash}">dashboard</a>.</p>
           <p>Ready to go live? <a href="${upgrade}">Upgrade to Pro →</a></p>`,
        ),
      };
    case "day13":
      return {
        subject: "Your paper-trading access expires tomorrow",
        html: wrap(
          `<h2>Your trial ends tomorrow</h2>
           <p>To keep the algorithm running — and unlock real-money execution — upgrade to Pro before
           your trial expires.</p>
           <p><a href="${upgrade}">Upgrade to Pro →</a></p>`,
        ),
      };
    case "expired":
      return {
        subject: "Your trial has expired — the algorithm is paused",
        html: wrap(
          `<h2>Your trial has expired</h2>
           <p>The algorithm is paused on your account. Upgrade to Pro to resume signals, paper trading,
           and live execution.</p>
           <p><a href="${upgrade}">Resume with Pro →</a></p>`,
        ),
      };
  }
}

/**
 * Send one drip email, at most once per user per stage. Idempotency is enforced by
 * stamping the matching `*_email_sent_at` column before sending (best-effort).
 */
export async function sendDripEmail(
  admin: AdminClient,
  args: { userId: string; email: string; kind: DripKind; daysLeft?: number | null },
): Promise<SendEmailResult> {
  const column = DRIP_COLUMN[args.kind];

  const { data: prof } = await admin
    .from("profiles")
    .select("user_id, welcome_email_sent_at, day7_email_sent_at, day13_email_sent_at, expired_email_sent_at")
    .eq("user_id", args.userId)
    .maybeSingle();

  if (!prof) return { sent: false, skipped: true };
  if ((prof as Record<string, unknown>)[column]) return { sent: false, skipped: true };

  // Stamp first so a retry/double-fire cannot send twice.
  await admin.from("profiles").update({ [column]: new Date().toISOString() }).eq("user_id", args.userId);

  const { subject, html } = template(args.kind, args.daysLeft ?? null);
  const result = await sendEmail({ to: args.email, subject, html });

  // If the provider call failed, clear the stamp so a later run can retry.
  if (!result.sent && !result.skipped) {
    await admin.from("profiles").update({ [column]: null }).eq("user_id", args.userId);
  }
  return result;
}
