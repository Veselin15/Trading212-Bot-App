import { createSupabaseAdminClient } from "@/lib/supabase/admin";

/** Returns null when core tables exist; otherwise a short setup message. */
export async function getSupabaseSchemaSetupMessage(): Promise<string | null> {
  const admin = createSupabaseAdminClient();

  const checks = await Promise.all([
    admin.from("subscriptions").select("id", { head: true, count: "exact" }),
    admin.from("licenses").select("id", { head: true, count: "exact" }),
  ]);

  const missing = checks.some((r) => r.error && /relation|schema cache|does not exist/i.test(r.error.message));
  if (!missing) return null;

  return "Database tables are missing. Run the SQL files in supabase/migrations/ in your Supabase project (SQL Editor), oldest first.";
}
