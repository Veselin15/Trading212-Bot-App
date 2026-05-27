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
          "h-full rounded-3xl bg-gradient-to-br from-emerald-400/25 via-white/10 to-teal-500/20 p-px transition-all duration-300 ease-out",
          "group-hover/gh:from-emerald-300/50 group-hover/gh:via-emerald-500/20 group-hover/gh:to-teal-400/35",
          "group-hover/gh:shadow-[0_0_40px_-10px_rgba(0,230,118,0.35)]",
        )}
      >
        <Card
          {...cardProps}
          className={cx(
            "h-full rounded-[calc(1.5rem-2px)] border-white/[0.08] bg-[#08080c] transition-[border-color,box-shadow,background-color] duration-300 ease-out",
            "group-hover/gh:border-emerald-500/30 group-hover/gh:bg-[#0a0a10]",
            "group-hover/gh:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.07),0_20px_40px_-28px_rgba(0,0,0,0.8)]",
            className,
          )}
        >
          {children}
        </Card>
      </div>
    </motion.div>
  );
}
