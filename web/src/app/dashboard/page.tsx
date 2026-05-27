import { redirect } from "next/navigation";

import { getMyLicenseKey } from "@/lib/license";
import { revokeLicensesIfSubscriptionTerminal } from "@/lib/billing-license-sync";
import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
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

  await refreshSubscriptionRowFromStripe(data.user.id, { email: data.user.email });

  const admin = createSupabaseAdminClient();
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

  const [{ subscription }, licenseKey, schemaSetupMessage] = await Promise.all([
    getMySubscription(),
    getMyLicenseKey(),
    getSupabaseSchemaSetupMessage(),
  ]);

  return (
    <DashboardShell
      userEmail={data.user.email ?? null}
      subscription={subscription}
      licenseKey={licenseKey}
      planTier={canUseProFeatures(subscription) ? "pro" : "free"}
      stripeCheckoutEnabled={isStripeCheckoutConfigured()}
      stripePortalEnabled={isStripePortalConfigured()}
      schemaSetupMessage={schemaSetupMessage}
    />
  );
}

