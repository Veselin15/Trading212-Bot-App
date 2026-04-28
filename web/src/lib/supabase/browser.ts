import { createBrowserClient } from "@supabase/ssr";

export function createSupabaseBrowserClient() {
  // Use static env access so Next.js can inline NEXT_PUBLIC_* at build time.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url) throw new Error("Missing required env var: NEXT_PUBLIC_SUPABASE_URL");
  if (!anon) throw new Error("Missing required env var: NEXT_PUBLIC_SUPABASE_ANON_KEY");
  return createBrowserClient(url, anon);
}

