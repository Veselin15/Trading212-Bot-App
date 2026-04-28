"use server";

import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

function getCreds(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  return { email, password };
}

export async function signIn(formData: FormData): Promise<{ error?: string } | void> {
  const { email, password } = getCreds(formData);
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };

  redirect("/account");
}

export async function signUp(formData: FormData): Promise<{ error?: string } | void> {
  const { email, password } = getCreds(formData);
  const supabase = await createSupabaseServerClient();

  const { error } = await supabase.auth.signUp({ email, password });
  if (error) return { error: error.message };

  redirect("/account");
}

