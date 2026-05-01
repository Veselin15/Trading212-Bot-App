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
          <div className="text-sm font-medium text-slate-300">Paper / Free</div>
          <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
            <AnimatedEuro end={0} label="free-tier" />
          </div>
          <div className="mt-2 text-sm text-slate-300">Explore the flow and the portal experience.</div>
          <ul className="mt-6 space-y-2 text-sm text-slate-200">
            <li>Portal access</li>
            <li>Account + license management</li>
            <li>Desktop download (gated)</li>
          </ul>
          <div className="mt-7">
            <ButtonLink href="/login" variant="secondary" className="w-full sm:w-auto">
              Start free
            </ButtonLink>
          </div>
        </GlowHoverCard>
      </motion.div>

      <motion.div variants={reduce ? fadeUpItemInstant : fadeUpItem}>
        <GlowHoverCard variant="accent" className="relative overflow-hidden p-7">
          <div className="absolute -right-24 -top-24 h-56 w-56 rounded-full bg-sky-500/20 blur-3xl" />
          <div className="relative">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-sky-200">Pro Automation</div>
              <div className="rounded-full border border-sky-500/30 bg-slate-950/40 px-2 py-1 text-xs text-slate-200">
                Most popular
              </div>
            </div>
            <div className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
              <AnimatedEuro end={49} label="pro-tier" />
            </div>
            <div className="mt-2 text-sm text-slate-300">Realtime signals + automated desktop execution.</div>
            <ul className="mt-6 space-y-2 text-sm text-slate-200">
              <li>Signals feed (RLS gated)</li>
              <li>License key for the executor</li>
              <li>Desktop download access</li>
            </ul>
            <div className="mt-7">
              <ButtonLink href="/login" className="w-full sm:w-auto">
                Upgrade to Pro
              </ButtonLink>
            </div>
            <div className="mt-4 text-xs text-slate-400">
              Your Trading212 API key is entered only in the desktop app, never on the website.
            </div>
          </div>
        </GlowHoverCard>
      </motion.div>

      <motion.div variants={reduce ? fadeUpItemInstant : fadeUpItem}>
        <GlowHoverCard className="p-7">
          <div className="text-sm font-medium text-slate-300">Enterprise</div>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">Custom onboarding</div>
          <div className="mt-2 text-sm text-slate-300">
            Dedicated support, custom execution logic, and tailored access controls.
          </div>
          <ul className="mt-6 space-y-2 text-sm text-slate-200">
            <li>Priority support</li>
            <li>Custom broker connectors</li>
            <li>Custom compliance constraints</li>
          </ul>
          <div className="mt-7">
            <a
              className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-slate-800/90 bg-white/5 px-5 text-sm font-medium text-slate-50 backdrop-blur transition-colors hover:bg-white/10"
              href="mailto:support@example.com"
            >
              Contact
            </a>
          </div>
        </GlowHoverCard>
      </motion.div>
    </motion.div>
  );
}
