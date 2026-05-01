"use client";

import { motion, useReducedMotion } from "framer-motion";
import { type ReactNode } from "react";

import { fadeUpItem, fadeUpItemInstant, fadeUpParent, fadeUpParentInstant } from "@/components/motion/variants";

export function HeroGridMotion({ left, right }: { left: ReactNode; right: ReactNode }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="grid items-start gap-10 lg:grid-cols-12 lg:gap-12"
      variants={reduce ? fadeUpParentInstant : fadeUpParent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.08, margin: "0px 0px -40px 0px" }}
    >
      <motion.div
        variants={reduce ? fadeUpItemInstant : fadeUpItem}
        className="order-2 lg:order-1 lg:col-span-7"
      >
        {left}
      </motion.div>
      <motion.div
        variants={reduce ? fadeUpItemInstant : fadeUpItem}
        className="order-1 lg:order-2 lg:col-span-5"
      >
        {right}
      </motion.div>
    </motion.div>
  );
}
