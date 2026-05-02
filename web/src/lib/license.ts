import { createSupabaseServerClient } from "@/lib/supabase/server";

/** Latest active license key for the signed-in user, or null. */
export async function getMyLicenseKey(): Promise<string | null> {
  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) return null;

  const { data } = await supabase
    .from("licenses")
    .select("license_key")
    .eq("user_id", userRes.user.id)
    .eq("status", "active")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!data?.license_key) return null;
  return String(data.license_key);
}
