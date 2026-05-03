"use client";

import { type ReactNode, useCallback, useRef, useState } from "react";

export function HeroSpotlightCard({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [glow, setGlow] = useState({ x: 50, y: 35 });

  const move = useCallback((clientX: number, clientY: number) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = ((clientX - r.left) / r.width) * 100;
    const y = ((clientY - r.top) / r.height) * 100;
    setGlow({ x, y });
  }, []);

  return (
    <div
      ref={ref}
      onPointerMove={(e) => {
        if (e.pointerType === "mouse") move(e.clientX, e.clientY);
      }}
      onPointerLeave={() => setGlow({ x: 50, y: 35 })}
      className="group/spot relative mt-6 overflow-hidden rounded-2xl border-2 border-emerald-400/35 bg-gradient-to-br from-emerald-500/20 via-[#0A0A0A] to-black p-5 shadow-lg shadow-emerald-500/10 transition-[border-color,box-shadow] duration-300 hover:border-emerald-400/50 hover:shadow-emerald-500/20 sm:p-6"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-70 transition-opacity duration-500 motion-reduce:opacity-30"
        style={{
          background: `radial-gradient(520px circle at ${glow.x}% ${glow.y}%, rgba(16,185,129,0.22), transparent 55%)`,
        }}
        aria-hidden
      />
      <div className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-emerald-400/20 blur-3xl transition-transform duration-700 ease-out group-hover/spot:scale-110" />
      <div className="relative">{children}</div>
    </div>
  );
}
