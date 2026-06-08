import { cache } from "react";
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

import { requiredPublicEnv } from "@/lib/env";

export async function createSupabaseServerClient() {
  const cookieStore = await cookies();

  return createServerClient(requiredPublicEnv("NEXT_PUBLIC_SUPABASE_URL"), requiredPublicEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"), {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // Server Components may throw if cookies are set outside of a Route Handler.
          // Middleware handles refresh in a safe place.
        }
      },
    },
  });
}

/**
 * The authenticated user, validated against Supabase's auth server.
 *
 * Wrapped in React `cache()` so the (network) `getUser()` round-trip runs at most
 * once per request — the root-layout header and the page both call this, and so do
 * the subscription/profile/license helpers below.
 */
export const getServerUser = cache(async () => {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.getUser();
  if (error) return null;
  return data.user ?? null;
});

