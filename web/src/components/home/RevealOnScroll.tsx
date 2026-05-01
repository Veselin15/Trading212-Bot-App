"use client";

import { motion, useReducedMotion } from "framer-motion";
import { type ReactNode } from "react";

import { easeOutSnappy } from "@/components/motion/variants";

export function RevealOnScroll({
  children,
  className = "",
  delayMs = 0,
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
}) {
  const reduce = useReducedMotion();

  if (reduce) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, amount: 0.12, margin: "0px 0px -32px 0px" }}
      transition={{
        duration: 0.42,
        delay: delayMs / 1000,
        ease: easeOutSnappy,
      }}
    >
      {children}
    </motion.div>
  );
}
