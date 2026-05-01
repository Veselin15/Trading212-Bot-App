import { getServerUser } from "@/lib/supabase/server";
import { SiteHeaderClient } from "@/components/SiteHeaderClient";

export async function SiteHeader() {
  const user = await getServerUser();
  const isAuthed = Boolean(user);

  return <SiteHeaderClient isAuthed={isAuthed} />;
}

