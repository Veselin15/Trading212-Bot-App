"use client";

import { useState } from "react";

const ITEMS = [
  {
    label: "Standard Invest account",
    detail: "Works with the same account you already use — no new broker onboarding.",
  },
  {
    label: "Long-only strategy",
    detail: "Designed for buy-and-hold style investing, not leveraged or short positions.",
  },
  {
    label: "No specialised trading account",
    detail: "No margin account, no options chain — keep complexity off your plate.",
  },
] as const;

export function FeaturePills() {
  const [active, setActive] = useState<number | null>(null);

  return (
    <ul className="mt-4 flex flex-wrap gap-2" role="list">
      {ITEMS.map((item, i) => {
        const on = active === i;
        return (
          <li key={item.label}>
            <button
              type="button"
              onClick={() => setActive(on ? null : i)}
              className={`rounded-full border px-3 py-1.5 text-left text-xs font-medium transition-all duration-200 sm:text-sm ${
                on
                  ? "scale-[1.02] border-sky-400/50 bg-sky-500/20 text-sky-50 shadow-md shadow-sky-500/10 ring-1 ring-sky-400/30"
                  : "border-sky-400/25 bg-slate-950/50 text-sky-100 hover:border-sky-400/40 hover:bg-sky-500/10 hover:text-sky-50 active:scale-[0.98]"
              }`}
            >
              <span className="block">{item.label}</span>
              <span
                className={`mt-1 block max-w-[min(100vw-4rem,20rem)] text-[11px] font-normal leading-snug text-sky-200/90 transition-[max-height,opacity,margin] duration-200 sm:max-w-xs ${
                  on ? "mt-1 max-h-28 opacity-100" : "mt-0 max-h-0 overflow-hidden opacity-0"
                }`}
              >
                {item.detail}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
