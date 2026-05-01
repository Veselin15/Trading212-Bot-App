"use client";

import { motion, useReducedMotion } from "framer-motion";

import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { easeOutSnappy } from "@/components/motion/variants";

export function ProductDisclaimer() {
  const reduce = useReducedMotion();

  if (reduce) {
    return (
      <GlowHoverCard className="p-7">
        <h2 className="text-2xl font-semibold tracking-tight">Risk & disclaimer</h2>
        <div className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
          <p>
            Trading is risky. This product is tooling (software) that can automate execution; it does not guarantee
            profits, and you can lose money.
          </p>
          <p>
            Backtests are simulations and can differ materially from live results due to slippage, spreads, outages, and
            market regime changes.
          </p>
          <p>
            Always review the settings and ensure the executor is running on hardware you control. You are responsible
            for your Trading212 account and decisions.
          </p>
        </div>
      </GlowHoverCard>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.38, ease: easeOutSnappy }}
    >
      <GlowHoverCard className="p-7">
        <h2 className="text-2xl font-semibold tracking-tight">Risk & disclaimer</h2>
        <div className="mt-3 space-y-2 text-sm leading-6 text-slate-300">
          <p>
            Trading is risky. This product is tooling (software) that can automate execution; it does not guarantee
            profits, and you can lose money.
          </p>
          <p>
            Backtests are simulations and can differ materially from live results due to slippage, spreads, outages, and
            market regime changes.
          </p>
          <p>
            Always review the settings and ensure the executor is running on hardware you control. You are responsible
            for your Trading212 account and decisions.
          </p>
        </div>
      </GlowHoverCard>
    </motion.div>
  );
}
