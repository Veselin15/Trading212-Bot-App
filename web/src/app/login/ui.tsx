"use client";

import { useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

import { signIn, signUp } from "./actions";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(formData: FormData) {
    setError(null);
    const res = mode === "signin" ? await signIn(formData) : await signUp(formData);
    if (res?.error) setError(res.error);
  }

  async function onGoogle() {
    setError(null);
    setBusy(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error: oauthErr } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/auth/callback` },
      });
      if (oauthErr) setError(oauthErr.message);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        onClick={onGoogle}
        disabled={busy}
        className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 bg-white px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 disabled:opacity-60 dark:border-white/10 dark:bg-zinc-950 dark:text-zinc-50 dark:hover:bg-zinc-900"
      >
        Continue with Google
      </button>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-black/10 dark:bg-white/10" />
        <div className="text-xs text-zinc-500">or</div>
        <div className="h-px flex-1 bg-black/10 dark:bg-white/10" />
      </div>

      <form action={onSubmit} className="flex flex-col gap-3">
      <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Email</label>
      <input
        name="email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        className="h-11 rounded-xl border border-black/10 bg-white px-3 text-sm text-zinc-950 outline-none focus:ring-2 focus:ring-zinc-400 dark:border-white/10 dark:bg-zinc-950 dark:text-zinc-50"
        placeholder="you@example.com"
      />

      <label className="mt-2 text-sm font-medium text-zinc-900 dark:text-zinc-100">Password</label>
      <input
        name="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        className="h-11 rounded-xl border border-black/10 bg-white px-3 text-sm text-zinc-950 outline-none focus:ring-2 focus:ring-zinc-400 dark:border-white/10 dark:bg-zinc-950 dark:text-zinc-50"
        placeholder="••••••••"
      />

      {error ? (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className="mt-3 inline-flex h-11 items-center justify-center rounded-xl bg-zinc-950 px-5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200"
      >
        {mode === "signin" ? "Sign in" : "Create account"}
      </button>

      <button
        type="button"
        onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
        className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 px-5 text-sm font-medium text-zinc-950 hover:bg-zinc-50 dark:border-white/10 dark:text-zinc-50 dark:hover:bg-zinc-900"
      >
        {mode === "signin" ? "Need an account? Sign up" : "Already have an account? Sign in"}
      </button>
      </form>
    </div>
  );
}

