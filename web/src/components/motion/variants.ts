import type { Variants } from "framer-motion";

/** Snappy, institutional-style easing (approx. easeOut cubic) */
export const easeOutSnappy: [number, number, number, number] = [0.22, 1, 0.36, 1];

export const fadeUpParent: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.1, delayChildren: 0.04 },
  },
};

export const fadeUpItem: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.36, ease: easeOutSnappy },
  },
};

export const fadeUpParentInstant: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0, delayChildren: 0 },
  },
};

export const fadeUpItemInstant: Variants = {
  hidden: { opacity: 1, y: 0 },
  visible: { opacity: 1, y: 0 },
};
