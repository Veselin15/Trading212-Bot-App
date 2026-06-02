import { type SubscriptionRow, activePaidPlan } from "@/lib/subscription-model";

/**
 * Effective access tier, computed at read time. Mirrors `public.effective_tier`
 * in SQL and `resolve_license_tier` in the FastAPI backend:
 *
 *   active subscription, plan=pro       -> PRO     (full signal feed, live, 10 positions)
 *   active subscription, plan=starter   -> STARTER (core signals, live, 3 positions)
 *   else trial_ends_at in future        -> TRIAL   (full feed, paper only)
 *   else                                -> EXPIRED (locked until upgrade)
 */
export type EffectiveTier = "TRIAL" | "STARTER" | "PRO" | "EXPIRED";

export type ProfileRow = {
  subscription_tier: string;
  trial_ends_at: string | null;
};

/** Per-tier product capabilities. Single source of truth shared across UI + copy. */
export type TierCapabilities = {
  /** Real-money (live) execution is unlocked. */
  liveTrading: boolean;
  /** Whether the extended ("Pro-only") signal feed is delivered. */
  fullSignalFeed: boolean;
  /** Max concurrent open positions the desktop executor will hold. */
  maxOpenPositions: number;
  label: string;
  /** Monthly price in EUR, or null for the free trial. */
  priceEur: number | null;
};

export const TIER_CAPABILITIES: Record<EffectiveTier, TierCapabilities> = {
  TRIAL: { liveTrading: false, fullSignalFeed: true, maxOpenPositions: 2, label: "Free trial", priceEur: null },
  STARTER: { liveTrading: true, fullSignalFeed: false, maxOpenPositions: 3, label: "Starter", priceEur: 19 },
  PRO: { liveTrading: true, fullSignalFeed: true, maxOpenPositions: 10, label: "Pro", priceEur: 49 },
  EXPIRED: { liveTrading: false, fullSignalFeed: false, maxOpenPositions: 0, label: "Expired", priceEur: null },
};

export function tierCapabilities(tier: EffectiveTier): TierCapabilities {
  return TIER_CAPABILITIES[tier];
}

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
  const plan = activePaidPlan(subscription);
  if (plan === "pro") return "PRO";
  if (plan === "starter") return "STARTER";
  if (trialActive(profile, now.getTime())) return "TRIAL";
  return "EXPIRED";
}

/** A paying (non-trial, non-expired) tier. */
export function isPaidTier(tier: EffectiveTier): boolean {
  return tier === "STARTER" || tier === "PRO";
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
  return tier !== "EXPIRED";
}
