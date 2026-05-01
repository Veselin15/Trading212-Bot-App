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
      className="group/spot relative mt-6 overflow-hidden rounded-2xl border-2 border-sky-400/35 bg-gradient-to-br from-sky-500/20 via-slate-950/80 to-slate-950/90 p-5 shadow-lg shadow-sky-500/10 transition-[border-color,box-shadow] duration-300 hover:border-sky-400/50 hover:shadow-sky-500/20 sm:p-6"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-70 transition-opacity duration-500 motion-reduce:opacity-30"
        style={{
          background: `radial-gradient(520px circle at ${glow.x}% ${glow.y}%, rgba(56,189,248,0.22), transparent 55%)`,
        }}
        aria-hidden
      />
      <div className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-sky-400/20 blur-3xl transition-transform duration-700 ease-out group-hover/spot:scale-110" />
      <div className="relative">{children}</div>
    </div>
  );
}
