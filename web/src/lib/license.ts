import { createSupabaseServerClient } from "@/lib/supabase/server";

export type LicenseRow = {
  license_key: string;
  status: string;
  revoked_at: string | null;
  created_at: string;
};

export async function getMyLicense() {
  const supabase = await createSupabaseServerClient();

  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) return { user: null, license: null };

  const { data } = await supabase
    .from("licenses")
    .select("license_key,status,revoked_at,created_at")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return { user: userRes.user, license: (data as LicenseRow | null) ?? null };
}

