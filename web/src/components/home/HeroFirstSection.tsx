"use client";

/**
 * Hero landing — two-column layout: copy + spotlight on the left,
 * interactive graphic on the right (no heavy “integration diagram” card).
 */

import { motion, useReducedMotion } from "framer-motion";
import { Users } from "lucide-react";

import { easeOutSnappy } from "@/components/motion/variants";
import { EUMapIcon } from "@/components/EUMapIcon";
import { ButtonLink } from "@/components/ui/Button";
import { FeaturePills } from "@/components/home/FeaturePills";
import { HeroInteractiveGraphic } from "@/components/home/HeroInteractiveGraphic";
import { HeroSpotlightCard } from "@/components/home/HeroSpotlightCard";

export function HeroFirstSection() {
  const reduce = useReducedMotion();

  return (
    <div className="grid items-start gap-12 lg:grid-cols-12 lg:gap-x-10 lg:gap-y-0">
      <motion.div
        id="overview"
        className="scroll-mt-24 max-w-2xl text-left lg:col-span-6 xl:col-span-7"
        initial={reduce ? false : { opacity: 0, y: 14 }}
        whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.38, ease: easeOutSnappy }}
      >
        <div className="inline-flex cursor-default items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-slate-300 shadow-sm backdrop-blur transition-all duration-300 hover:border-emerald-500/50 hover:bg-emerald-500/[0.15]">
          <EUMapIcon className="text-emerald-200" title="EU market" />
          <span className="font-medium text-emerald-200">Built for the EU market</span>
          <span className="text-slate-400">EU stocks only · Trading212</span>
        </div>

        <h1 className="mt-4 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          The only Trading212 bot built exclusively for EU investors
        </h1>

        <p className="mt-5 max-w-xl text-pretty text-base leading-7 text-slate-300">
          100% EU-listed stocks. No US withholding friction. Automated signals delivered to your PC — your Trading212 API key stays local, never leaves your machine.
        </p>

        <HeroSpotlightCard>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/25 text-emerald-200 ring-1 ring-emerald-400/30 transition-transform duration-300 group-hover/spot:scale-105 motion-reduce:transform-none">
              <Users className="h-5 w-5" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-200/90 sm:text-sm">
                Made for EU residents on Trading212
              </p>
              <p className="mt-2 text-balance text-lg font-semibold leading-snug text-slate-50 sm:text-xl sm:leading-snug">
                Invest in EU-listed stocks — avoid US dividend withholding tax entirely.
              </p>
              <p className="mt-3 text-pretty text-sm leading-6 text-slate-200 sm:text-base sm:leading-7">
                The bot trades only EU-listed equities (Xetra, Euronext, etc.), keeping dividend friction close to zero for EU residents — no W-8BEN complexity, no 15–30% US withholding. Tap a pill for details.
              </p>
              <FeaturePills />
            </div>
          </div>
        </HeroSpotlightCard>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <ButtonLink href="/login" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
            Create account
          </ButtonLink>
          <ButtonLink href="/pricing" variant="secondary" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
            View pricing
          </ButtonLink>
        </div>

        <p className="mt-8 text-xs leading-5 text-slate-500">
          Not financial advice. Trading involves risk; past results do not guarantee future returns. Tax depends on your
          country — not tax advice.
        </p>
      </motion.div>

      <motion.div
        className="relative lg:col-span-6 xl:col-span-5"
        initial={reduce ? false : { opacity: 0, y: 16 }}
        whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.15 }}
        transition={{ duration: 0.4, ease: easeOutSnappy, delay: 0.05 }}
      >
        <HeroInteractiveGraphic />
      </motion.div>
    </div>
  );
}
