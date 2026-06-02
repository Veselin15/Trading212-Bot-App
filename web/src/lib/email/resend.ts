/**
 * Minimal Resend sender. No-ops (returns { sent: false }) until RESEND_API_KEY is set,
 * so the trial drip can be scaffolded now and switched on later by adding the env var.
 *
 * Wiring checklist (Phase 5):
 *   1. Create a Resend account + verified sending domain.
 *   2. Set RESEND_API_KEY and EMAIL_FROM (e.g. "SwiftTrade <noreply@swifttrade.app>").
 *   3. Point a scheduler at /api/cron/trial-emails (see that route) with CRON_SECRET.
 */
export type SendEmailResult = { sent: boolean; skipped?: boolean; error?: string };

export function isEmailConfigured(): boolean {
  return Boolean(process.env.RESEND_API_KEY && process.env.EMAIL_FROM);
}

export async function sendEmail(args: { to: string; subject: string; html: string }): Promise<SendEmailResult> {
  if (!isEmailConfigured()) {
    // Not wired yet — log so it is visible in dev without failing the request.
    console.info(`[email] skipped (RESEND not configured): "${args.subject}" -> ${args.to}`);
    return { sent: false, skipped: true };
  }

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: process.env.EMAIL_FROM,
        to: args.to,
        subject: args.subject,
        html: args.html,
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return { sent: false, error: `Resend ${res.status}: ${detail.slice(0, 200)}` };
    }
    return { sent: true };
  } catch (err) {
    return { sent: false, error: String(err) };
  }
}
