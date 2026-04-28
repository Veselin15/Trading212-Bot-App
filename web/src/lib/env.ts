export function requiredEnv(name: string): string {
  const v = process.env[name];
  if (!v) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return v;
}

// IMPORTANT:
// Next.js only inlines env vars when accessed statically (process.env.MY_VAR).
// These helpers avoid dynamic lookups for NEXT_PUBLIC_* values in middleware/client bundles.
export function requiredPublicEnv(
  name: "NEXT_PUBLIC_SUPABASE_URL" | "NEXT_PUBLIC_SUPABASE_ANON_KEY" | "NEXT_PUBLIC_SITE_URL",
): string {
  const v =
    name === "NEXT_PUBLIC_SUPABASE_URL"
      ? process.env.NEXT_PUBLIC_SUPABASE_URL
      : name === "NEXT_PUBLIC_SUPABASE_ANON_KEY"
        ? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
        : process.env.NEXT_PUBLIC_SITE_URL;

  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

