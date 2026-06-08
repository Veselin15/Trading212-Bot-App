import { cache } from "react";

import { createSupabaseServerClient, getServerUser } from "@/lib/supabase/server";

/** Latest active license key for the signed-in user, or null. Memoized per request. */
export const getMyLicenseKey = cache(async (): Promise<string | null> => {
  const user = await getServerUser();
  if (!user) return null;

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase
    .from("licenses")
    .select("license_key")
    .eq("user_id", user.id)
    .eq("status", "active")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!data?.license_key) return null;
  return String(data.license_key);
});
