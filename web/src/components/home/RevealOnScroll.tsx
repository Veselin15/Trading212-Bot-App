"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

export function RevealOnScroll({
  children,
  className = "",
  delayMs = 0,
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      queueMicrotask(() => setVisible(true));
      return;
    }

    const obs = new IntersectionObserver(
      ([e]) => {
        if (!e?.isIntersecting) return;
        window.setTimeout(() => setVisible(true), delayMs);
        obs.disconnect();
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [delayMs]);

  return (
    <div
      ref={ref}
      className={`transform-gpu transition-[opacity,transform,filter] duration-700 ease-out motion-safe:duration-[850ms] ${
        visible
          ? "translate-y-0 opacity-100 motion-safe:blur-none"
          : "translate-y-8 opacity-0 motion-safe:blur-sm"
      } ${className}`}
    >
      {children}
    </div>
  );
}
