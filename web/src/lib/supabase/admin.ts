import { createClient } from "@supabase/supabase-js";

import { requiredEnv, requiredPublicEnv } from "@/lib/env";

export function createSupabaseAdminClient() {
  return createClient(requiredPublicEnv("NEXT_PUBLIC_SUPABASE_URL"), requiredEnv("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

