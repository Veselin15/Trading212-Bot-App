import { redirect } from "next/navigation";

import { getMyLicenseKey } from "@/lib/license";
import { ensureSubscriberLicense, revokeLicensesIfSubscriptionTerminal } from "@/lib/billing-license-sync";
import { ensureProfileForUser, getMyProfile } from "@/lib/profile";
import { getMySubscription } from "@/lib/subscription";
import { computeEffectiveTier, trialDaysLeft } from "@/lib/tier";
import { isStripeCheckoutConfigured, isStripePortalConfigured } from "@/lib/stripe-env";
import { refreshSubscriptionRowFromStripe } from "@/lib/stripe-subscription-refresh";
import { getSupabaseSchemaSetupMessage } from "@/lib/supabase/schema-health";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

import { DashboardShell } from "./DashboardShell";

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();

  if (!data.user) redirect("/login");

  const admin = createSupabaseAdminClient();
  await ensureProfileForUser(admin, data.user.id);
  await refreshSubscriptionRowFromStripe(data.user.id, { email: data.user.email });

  const { data: statusRow } = await admin
    .from("subscriptions")
    .select("status")
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (statusRow?.status) {
    await revokeLicensesIfSubscriptionTerminal(admin, data.user.id, String(statusRow.status));
  }

  const [{ subscription }, profile, schemaSetupMessage] = await Promise.all([
    getMySubscription(),
    getMyProfile(),
    getSupabaseSchemaSetupMessage(),
  ]);

  const effectiveTier = computeEffectiveTier(subscription, profile);

  // Trial and paid users get a working license key so they can run the desktop app.
  if (effectiveTier !== "EXPIRED") {
    await ensureSubscriberLicense(admin, data.user.id);
  }
  const licenseKey = await getMyLicenseKey();

  return (
    <DashboardShell
      userEmail={data.user.email ?? null}
      subscription={subscription}
      licenseKey={licenseKey}
      effectiveTier={effectiveTier}
      trialDaysLeft={trialDaysLeft(profile)}
      stripeCheckoutEnabled={isStripeCheckoutConfigured()}
      stripePortalEnabled={isStripePortalConfigured()}
      schemaSetupMessage={schemaSetupMessage}
    />
  );
}

