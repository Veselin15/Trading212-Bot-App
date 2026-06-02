"use client";

import { motion, useReducedMotion } from "framer-motion";

import { GlowHoverCard } from "@/components/motion/GlowHoverCard";
import { fadeUpItem, fadeUpItemInstant, fadeUpParent, fadeUpParentInstant } from "@/components/motion/variants";
import { ButtonLink } from "@/components/ui/Button";

import { AnimatedEuro } from "./AnimatedEuro";

export function PricingTiers() {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="mt-10 grid gap-6 lg:grid-cols-3"
      variants={reduce ? fadeUpParentInstant : fadeUpParent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.1, margin: "0px 0px -48px 0px" }}
    >
      <motion.div variants={reduce ? fadeUpItemInstant : fadeUpItem}>
        <GlowHoverCard className="p-7">
          <div className="text-sm font-medium text-slate-300">14-Day Free Trial</div>
          <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
            <AnimatedEuro end={0} label="trial-tier" />
          </div>
          <div className="mt-2 text-sm text-slate-300">Full signal feed in paper mode for 14 days. No card required.</div>
          <ul className="mt-6 space-y-2 text-sm text-slate-200">
            <li>Full signals feed (paper)</li>
            <li>Paper trading on your practice account</li>
            <li>Desktop app + license key</li>
          </ul>
          <div className="mt-7">
            <ButtonLink href="/login" variant="secondary" className="w-full sm:w-auto">
              Start free trial
            </ButtonLink>
          </div>
        </GlowHoverCard>
      </motion.div>

      <motion.div variants={reduce ? fadeUpItemInstant : fadeUpItem}>
        <GlowHoverCard className="p-7">
          <div className="text-sm font-medium text-sky-200">Starter</div>
          <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
            <AnimatedEuro end={19} label="starter-tier" />
          </div>
          <div className="mt-2 text-sm text-slate-300">Live trading on our highest-conviction core signals.</div>
          <ul className="mt-6 space-y-2 text-sm text-slate-200">
            <li>Live (real-money) auto-execution</li>
            <li>Core signals only</li>
            <li>Up to 3 concurrent positions</li>
          </ul>
          <div className="mt-7">
            <ButtonLink href="/pricing" variant="secondary" className="w-full sm:w-auto">
              Get Starter
            </ButtonLink>
          </div>
        </GlowHoverCard>
      </motion.div>

      <motion.div variants={reduce ? fadeUpItemInstant : fadeUpItem}>
        <GlowHoverCard variant="accent" className="relative overflow-hidden p-7">
          <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-emerald-500/20 blur-3xl" />
          <div className="relative">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-emerald-200">Pro</div>
              <div className="rounded-full border border-emerald-500/30 bg-[#0A0A0A] px-2 py-1 text-xs text-slate-200">
                Most popular
              </div>
            </div>
            <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
              <AnimatedEuro end={49} label="pro-tier" />
            </div>
            <div className="mt-2 text-sm text-slate-300">The complete signal feed and more concurrent positions.</div>
            <ul className="mt-6 space-y-2 text-sm text-slate-200">
              <li>Full signal feed — every opportunity</li>
              <li>Live (real-money) auto-execution</li>
              <li>Up to 10 concurrent positions</li>
            </ul>
            <div className="mt-7">
              <ButtonLink href="/pricing" className="w-full sm:w-auto">
                Get Pro
              </ButtonLink>
            </div>
            <div className="mt-4 text-xs text-slate-400">
              Your Trading212 API key is entered only in the desktop app, never on the website.
            </div>
          </div>
        </GlowHoverCard>
      </motion.div>
    </motion.div>
  );
}
