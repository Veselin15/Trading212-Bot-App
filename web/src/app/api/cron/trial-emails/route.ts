import { NextResponse } from "next/server";

import { sendDripEmail, type DripKind } from "@/lib/email/drip";
import { isEmailConfigured } from "@/lib/email/resend";
import { trialDaysLeft } from "@/lib/tier";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

/**
 * Trial email drip (Phase 5). NOT self-scheduling — point an external scheduler at this
 * route once a day (Cloudflare Cron Trigger, Vercel Cron, or a GitHub Action), passing
 * the shared secret. Until RESEND_API_KEY + CRON_SECRET are set it is a guarded no-op.
 *
 *   GET/POST /api/cron/trial-emails   header: x-cron-secret: <CRON_SECRET>
 */
export const dynamic = "force-dynamic";

async function handle(request: Request) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return NextResponse.json({ error: "CRON_SECRET not configured" }, { status: 503 });

  const provided = request.headers.get("x-cron-secret") ?? new URL(request.url).searchParams.get("secret");
  if (provided !== secret) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  if (!isEmailConfigured()) return NextResponse.json({ ok: true, skipped: "email not configured" });

  const admin = createSupabaseAdminClient();
  const nowIso = new Date().toISOString();
  const inDays = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString();

  // Each stage targets profiles still on TRIAL that have not yet received this email.
  function baseQuery() {
    return admin.from("profiles").select("user_id, trial_ends_at").eq("subscription_tier", "TRIAL");
  }

  const counts: Record<string, number> = { welcome: 0, day7: 0, day13: 0, expired: 0 };

  async function run(kind: DripKind, column: string, apply: (q: ReturnType<typeof baseQuery>) => unknown) {
    const query = apply(baseQuery()) as ReturnType<typeof baseQuery>;
    const { data, error } = await query.is(column, null).limit(500);
    if (error || !data) return;
    for (const row of data as { user_id: string; trial_ends_at: string | null }[]) {
      const { data: userRes } = await admin.auth.admin.getUserById(row.user_id);
      const email = userRes?.user?.email;
      if (!email) continue;
      const res = await sendDripEmail(admin, {
        userId: row.user_id,
        email,
        kind,
        daysLeft: trialDaysLeft({ subscription_tier: "TRIAL", trial_ends_at: row.trial_ends_at }),
      });
      if (res.sent) counts[kind] += 1;
    }
  }

  // day7: ~halfway (1–8 days left). day13: final day (0–2 days left). expired: trial_ends_at passed.
  await run("day7", "day7_email_sent_at", (q) => q.gt("trial_ends_at", inDays(1)).lte("trial_ends_at", inDays(8)));
  await run("day13", "day13_email_sent_at", (q) => q.gt("trial_ends_at", nowIso).lte("trial_ends_at", inDays(2)));
  await run("expired", "expired_email_sent_at", (q) => q.lte("trial_ends_at", nowIso));

  return NextResponse.json({ ok: true, sent: counts });
}

export async function POST(request: Request) {
  return handle(request);
}

export async function GET(request: Request) {
  return handle(request);
}
