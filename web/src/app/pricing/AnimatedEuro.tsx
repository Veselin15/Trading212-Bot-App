"use client";

import { useInView } from "framer-motion";
import { useRef } from "react";
import CountUp from "react-countup";

export function AnimatedEuro({ end, label }: { end: number; label: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-20px" });

  return (
    <span ref={ref} className="tabular-nums" aria-label={label}>
      €
      {end === 0 ? (
        "0"
      ) : inView ? (
        <CountUp duration={1.05} start={0} end={end} decimals={0} useEasing />
      ) : (
        "0"
      )}
    </span>
  );
}
