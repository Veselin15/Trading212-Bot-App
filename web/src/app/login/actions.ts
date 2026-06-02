"use server";

import { redirect } from "next/navigation";

import { sendDripEmail } from "@/lib/email/drip";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export type AuthActionResult = {
  error?: string;
  needsEmailConfirmation?: boolean;
};

function getCreds(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  return { email, password };
}

function siteUrl() {
  return process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app";
}

export async function signIn(formData: FormData): Promise<AuthActionResult | void> {
  const { email, password } = getCreds(formData);
  if (!email || !password) {
    return { error: "Email and password are required." };
  }

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };

  redirect("/dashboard");
}

export async function signUp(formData: FormData): Promise<AuthActionResult | void> {
  const { email, password } = getCreds(formData);
  if (!email || !password) {
    return { error: "Email and password are required." };
  }
  if (password.length < 6) {
    return { error: "Password must be at least 6 characters." };
  }

  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${siteUrl()}/auth/callback`,
    },
  });

  if (error) return { error: error.message };

  // Fire the Day-1 welcome email (no-op until Resend is configured). Best-effort.
  if (data.user?.id) {
    try {
      await sendDripEmail(createSupabaseAdminClient(), {
        userId: data.user.id,
        email,
        kind: "welcome",
      });
    } catch {
      // never block signup on email delivery
    }
  }

  // Supabase returns a session immediately when email confirmation is disabled.
  if (data.session) {
    redirect("/dashboard");
  }

  return {
    needsEmailConfirmation: true,
  };
}
