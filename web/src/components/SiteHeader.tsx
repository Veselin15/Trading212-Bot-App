import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
import { getServerUser } from "@/lib/supabase/server";
import { SiteHeaderClient } from "@/components/SiteHeaderClient";

export async function SiteHeader() {
  const user = await getServerUser();
  const isAuthed = Boolean(user);

  let hasProAccess = false;
  if (user) {
    const { subscription } = await getMySubscription();
    hasProAccess = canUseProFeatures(subscription);
  }

  return <SiteHeaderClient isAuthed={isAuthed} hasProAccess={hasProAccess} />;
}

