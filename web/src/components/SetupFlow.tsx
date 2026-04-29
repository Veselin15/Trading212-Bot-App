"use client";

import Link from "next/link";
import type { ComponentType } from "react";
import { ArrowRight, KeyRound, Laptop, ShieldCheck, UserRound } from "lucide-react";

type FlowItem = {
  icon: ComponentType<{ className?: string }>;
  title: string;
  body: string;
  cta?: { href: string; label: string };
};

const items: FlowItem[] = [
  {
    icon: UserRound,
    title: "1) Create your portal account",
    body: "Log in to see subscription status, manage your license, and access downloads.",
    cta: { href: "/login", label: "Create account" },
  },
  {
    icon: KeyRound,
    title: "2) Get a license key",
    body: "Your license key unlocks the desktop executor and gates access to the live feed (Pro).",
    cta: { href: "/dashboard", label: "Open dashboard" },
  },
  {
    icon: Laptop,
    title: "3) Install the Windows executor",
    body: "The desktop app is what actually executes orders. It runs on hardware you control.",
    cta: { href: "/download", label: "Download" },
  },
  {
    icon: ShieldCheck,
    title: "4) Connect Trading212 locally",
    body: "Paste your Trading212 API key inside the desktop app only. It’s stored encrypted on-device.",
    cta: { href: "/faq", label: "Why this is safer" },
  },
];

export function SetupFlow() {
  return (
    <div className="rounded-3xl border border-slate-800/70 bg-slate-950/40 p-5 shadow-sm backdrop-blur sm:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">At-a-glance</div>
          <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-50">
            From signup → connected executor (in minutes)
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            The portal manages access. The desktop app executes locally. No broker keys are entered in the browser.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] lg:items-stretch">
        {items.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={item.title} className="contents">
              <div className="rounded-2xl border border-slate-800/70 bg-white/5 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="text-sm font-medium text-slate-50">{item.title}</div>
                </div>
                <div className="mt-3 text-sm leading-6 text-slate-300">{item.body}</div>
                {item.cta ? (
                  <div className="mt-4">
                    <Link
                      href={item.cta.href}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-800/80 bg-white/5 px-3 py-2 text-xs font-medium text-slate-50 hover:bg-white/10"
                    >
                      {item.cta.label}
                      <ArrowRight className="h-4 w-4 text-slate-300" />
                    </Link>
                  </div>
                ) : null}
              </div>

              {idx < items.length - 1 ? (
                <div className="hidden items-center justify-center lg:flex">
                  <ArrowRight className="h-5 w-5 text-slate-600" />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="mt-5 rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-100">
        Trading is risky. This software can automate execution, but it does not guarantee profits.
      </div>
    </div>
  );
}

