"use client";

import { motion, useReducedMotion } from "framer-motion";

import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { fadeUpItem, fadeUpItemInstant, fadeUpParent, fadeUpParentInstant } from "@/components/motion/variants";

import { PRODUCT_FEATURES, PRODUCT_SETUP_STEPS } from "./features-data";

export function ProductFeatureGrid() {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="grid w-full min-w-0 gap-4 sm:grid-cols-2"
      variants={reduce ? fadeUpParentInstant : fadeUpParent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.08, margin: "0px 0px -48px 0px" }}
    >
      {PRODUCT_FEATURES.map(({ Icon, title, body }) => (
        <motion.div key={title} variants={reduce ? fadeUpItemInstant : fadeUpItem}>
          <GlowHoverCard className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <div className="text-sm font-medium text-slate-50">{title}</div>
            </div>
            <div className="mt-3 text-sm leading-6 text-slate-300">{body}</div>
          </GlowHoverCard>
        </motion.div>
      ))}
    </motion.div>
  );
}

export function ProductSetupGrid() {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="grid w-full min-w-0 gap-4 sm:grid-cols-3"
      variants={reduce ? fadeUpParentInstant : fadeUpParent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.1, margin: "0px 0px -40px 0px" }}
    >
      {PRODUCT_SETUP_STEPS.map((s) => (
        <motion.div key={s.title} variants={reduce ? fadeUpItemInstant : fadeUpItem}>
          <GlowHoverCard className="p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{s.step}</div>
            <div className="mt-2 text-sm font-medium text-slate-50">{s.title}</div>
            <div className="mt-2 text-sm leading-6 text-slate-300">{s.body}</div>
          </GlowHoverCard>
        </motion.div>
      ))}
    </motion.div>
  );
}
