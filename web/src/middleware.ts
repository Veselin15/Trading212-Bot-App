import { updateSession } from "@/lib/supabase/middleware";
import type { NextRequest } from "next/server";

// OpenNext on Cloudflare expects middleware.ts (Next 16 proxy.ts not fully supported yet).
export async function middleware(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
