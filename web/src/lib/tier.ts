import { type SubscriptionRow, canUseProFeatures } from "@/lib/subscription-model";

/**
 * Effective access tier, computed at read time. Mirrors `public.effective_tier`
 * in SQL and `resolve_license_tier` in the FastAPI backend:
 *
 *   active paid subscription      -> PRO    (live execution unlocked)
 *   else trial_ends_at in future  -> TRIAL  (paper trading + signals only)
 *   else                          -> EXPIRED (locked until upgrade)
 */
export type EffectiveTier = "TRIAL" | "PRO" | "EXPIRED";

export type ProfileRow = {
  subscription_tier: string;
  trial_ends_at: string | null;
};

function trialActive(profile: ProfileRow | null, now: number): boolean {
  if (!profile?.trial_ends_at) return false;
  const end = new Date(profile.trial_ends_at).getTime();
  return Number.isFinite(end) && end > now;
}

export function computeEffectiveTier(
  subscription: SubscriptionRow | null,
  profile: ProfileRow | null,
  now: Date = new Date(),
): EffectiveTier {
  if (canUseProFeatures(subscription)) return "PRO";
  if (trialActive(profile, now.getTime())) return "TRIAL";
  return "EXPIRED";
}

/** Whole days left in the trial (rounded up), or null when no trial window applies. */
export function trialDaysLeft(profile: ProfileRow | null, now: Date = new Date()): number | null {
  if (!profile?.trial_ends_at) return null;
  const end = new Date(profile.trial_ends_at).getTime();
  if (!Number.isFinite(end)) return null;
  const ms = end - now.getTime();
  if (ms <= 0) return 0;
  return Math.ceil(ms / 86_400_000);
}

/** Whether the user may hold a working license key (trial or paid, not expired). */
export function tierCanUseLicense(tier: EffectiveTier): boolean {
  return tier === "TRIAL" || tier === "PRO";
}
