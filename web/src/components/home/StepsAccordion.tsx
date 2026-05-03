"use client";

import { motion, useReducedMotion } from "framer-motion";
import { CreditCard, Download, Link2, UserPlus } from "lucide-react";
import { useState } from "react";

import {
  easeOutSnappy,
  fadeUpItem,
  fadeUpItemInstant,
  fadeUpParent,
  fadeUpParentInstant,
} from "@/components/motion/variants";
import { ButtonLink } from "@/components/ui/Button";

const STEPS = [
  {
    title: "Create your account",
    body: "Sign in and open the dashboard to see subscription status, your license key, and downloads.",
    Icon: UserPlus,
  },
  {
    title: "Upgrade when you are ready",
    body: "Subscribe to Pro for live signals and access to the Windows desktop executor.",
    Icon: CreditCard,
  },
  {
    title: "Install the desktop app",
    body: "Download the installer, run it on your PC, and keep Trading212 keys off the browser entirely.",
    Icon: Download,
  },
  {
    title: "Connect locally",
    body: "Paste your Trading212 API key only inside the desktop app, then add your license key. You are set.",
    Icon: Link2,
  },
] as const;

export function StepsAccordion() {
  const [open, setOpen] = useState(0);
  const reduce = useReducedMotion();
  const parentVars = reduce ? fadeUpParentInstant : fadeUpParent;
  const itemVars = reduce ? fadeUpItemInstant : fadeUpItem;

  return (
    <div className="mx-auto max-w-2xl">
      <motion.h2
        className="text-center text-xl font-semibold tracking-tight text-slate-50 sm:text-2xl"
        initial={reduce ? false : { opacity: 0, y: 14 }}
        whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.35 }}
        transition={{ duration: 0.34, ease: easeOutSnappy }}
      >
        Get started
      </motion.h2>
      <motion.p
        className="mx-auto mt-2 max-w-lg text-center text-sm text-slate-400"
        initial={reduce ? false : { opacity: 0, y: 12 }}
        whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.35 }}
        transition={{ duration: 0.34, ease: easeOutSnappy, delay: 0.04 }}
      >
        Open a step for details. Execution stays on your machine — nothing here touches your broker keys.
      </motion.p>

      <div className="mt-3 flex justify-center gap-1.5 sm:mt-4" role="tablist" aria-label="Steps">
        {STEPS.map((_, i) => {
          const isOpen = open === i;
          return (
            <button
              key={i}
              type="button"
              role="tab"
              aria-selected={isOpen}
              aria-controls={`step-${i}-panel`}
              id={`step-${i}-tab`}
              onClick={() => setOpen(i)}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                isOpen ? "w-8 bg-violet-400 shadow-sm shadow-violet-400/40" : "w-1.5 bg-slate-700 hover:bg-slate-600"
              }`}
            />
          );
        })}
      </div>

      <motion.div
        className="mt-8 space-y-3"
        role="list"
        variants={parentVars}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.08, margin: "0px 0px -40px 0px" }}
      >
        {STEPS.map((step, i) => {
          const isOpen = open === i;
          const Icon = step.Icon;
          return (
            <motion.div
              key={step.title}
              variants={itemVars}
              role="listitem"
              className={`relative overflow-hidden rounded-2xl border transition-all duration-300 ease-out ${
                isOpen
                  ? "border-violet-500/35 bg-gradient-to-br from-violet-500/[0.12] via-white/[0.06] to-background/85 shadow-lg shadow-violet-500/5 ring-1 ring-violet-400/20"
                  : "border-white/10 bg-white/[0.03] hover:border-slate-600/80 hover:bg-white/[0.06]"
              }`}
            >
              <button
                type="button"
                id={`step-${i}-btn`}
                aria-expanded={isOpen}
                aria-controls={`step-${i}-panel`}
                onClick={() => setOpen(isOpen ? -1 : i)}
                className="group flex w-full items-center justify-between gap-3 px-4 py-4 text-left sm:px-5 sm:py-4"
              >
                <span className="flex min-w-0 items-center gap-3 sm:gap-4">
                  <span
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors duration-300 ${
                      isOpen
                        ? "bg-violet-500/25 text-violet-100 ring-1 ring-violet-400/35"
                        : "bg-slate-900/80 text-slate-400 ring-1 ring-slate-700/80 group-hover:text-slate-200 group-hover:ring-slate-600/90"
                    }`}
                  >
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-violet-400/90">
                      Step {i + 1}
                    </span>
                    <span className="text-sm font-medium text-slate-50 sm:text-base">{step.title}</span>
                  </span>
                </span>
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-transform duration-300 ease-out ${
                    isOpen ? "rotate-90 text-violet-300" : ""
                  }`}
                  aria-hidden
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M6 12l4-4-4-4"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </button>
              <div
                id={`step-${i}-panel`}
                role="region"
                aria-labelledby={`step-${i}-btn`}
                className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:duration-150 ${
                  isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="min-h-0 overflow-hidden">
                  <p className="border-t border-slate-800/50 px-4 pb-4 pt-3 text-sm leading-6 text-slate-300 sm:px-5 sm:pb-5 sm:pl-[4.25rem] sm:pt-4">
                    {step.body}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <ButtonLink href="/product" variant="secondary" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
          Full product walkthrough
        </ButtonLink>
        <ButtonLink href="/download" className="transition-transform hover:scale-[1.02] active:scale-[0.98]">
          Download app
        </ButtonLink>
      </div>
    </div>
  );
}
