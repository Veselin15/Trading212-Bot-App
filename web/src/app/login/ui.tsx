"use client";

import { useState } from "react";
import { isRedirectError } from "next/dist/client/components/redirect-error";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { Button } from "@/components/ui/Button";

import { signIn, signUp, type AuthActionResult } from "./actions";

export function LoginForm({ oauthError }: { oauthError?: string | null }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(oauthError ?? null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(formData: FormData) {
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      const res: AuthActionResult | void =
        mode === "signin" ? await signIn(formData) : await signUp(formData);
      if (res?.error) setError(res.error);
      if (res?.needsEmailConfirmation) {
        setInfo("Account created. Check your email for a confirmation link, then sign in.");
        setMode("signin");
      }
    } catch (e) {
      if (isRedirectError(e)) throw e;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onGoogle() {
    setError(null);
    setInfo(null);
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
      <Button type="button" variant="secondary" onClick={onGoogle} disabled={busy}>
        Continue with Google
      </Button>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-white/10" />
        <div className="text-xs text-slate-500">or</div>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      <form action={onSubmit} className="flex flex-col gap-3">
        <label className="text-sm font-medium text-slate-200">Email</label>
        <input
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          className="h-11 rounded-xl border border-white/10 bg-white/[0.04] px-3 text-sm text-white shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)] outline-none transition-colors placeholder:text-slate-600 focus:border-emerald-500/40 focus:ring-2 focus:ring-emerald-500/25"
          placeholder="you@example.com"
        />

        <label className="mt-2 text-sm font-medium text-slate-200">Password</label>
        <input
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          autoComplete={mode === "signin" ? "current-password" : "new-password"}
          className="h-11 rounded-xl border border-white/10 bg-white/[0.04] px-3 text-sm text-white shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)] outline-none transition-colors placeholder:text-slate-600 focus:border-emerald-500/40 focus:ring-2 focus:ring-emerald-500/25"
          placeholder="••••••••"
        />

        {info ? (
          <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
            {info}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        ) : null}

        <Button type="submit" disabled={busy} className="mt-3">
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Start 14-day free trial"}
        </Button>

        {mode === "signup" && (
          <p className="text-center text-xs text-slate-500">14 days free · paper trade the algorithm · no card required</p>
        )}

        <Button
          type="button"
          variant="secondary"
          disabled={busy}
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError(null);
            setInfo(null);
          }}
        >
          {mode === "signin" ? "Need an account? Sign up" : "Already have an account? Sign in"}
        </Button>
      </form>
    </div>
  );
}
