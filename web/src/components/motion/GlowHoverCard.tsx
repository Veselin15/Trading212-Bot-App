"use client";

import { motion, useReducedMotion } from "framer-motion";
import { type ComponentProps, type ReactNode } from "react";

import { Card } from "@/components/ui/Card";

import { easeOutSnappy } from "./variants";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type CardProps = ComponentProps<typeof Card>;

export function GlowHoverCard({
  children,
  className,
  disableLift,
  ...cardProps
}: CardProps & { children: ReactNode; disableLift?: boolean }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="group/gh h-full rounded-3xl p-[1px] transition-shadow duration-200 ease-out"
      initial={false}
      whileHover={
        reduce || disableLift
          ? undefined
          : {
              y: -4,
              transition: { duration: 0.22, ease: easeOutSnappy },
            }
      }
    >
      <div
        className={cx(
          "h-full rounded-3xl bg-gradient-to-br from-emerald-500/20 via-slate-800/60 to-emerald-700/15 p-[1px] transition-all duration-200 ease-out",
          "group-hover/gh:from-emerald-400/45 group-hover/gh:via-slate-700/70 group-hover/gh:to-emerald-600/30",
          "group-hover/gh:shadow-[0_0_32px_-8px_rgba(16,185,129,0.28)]",
        )}
      >
        <Card
          {...cardProps}
          className={cx(
            "h-full rounded-[calc(1.5rem-2px)] border-white/10 bg-[#0A0A0A] transition-[border-color,box-shadow,background-color] duration-200 ease-out",
            "group-hover/gh:border-emerald-500/35 group-hover/gh:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]",
            "group-hover/gh:bg-[#0A0A0A]",
            className,
          )}
        >
          {children}
        </Card>
      </div>
    </motion.div>
  );
}
