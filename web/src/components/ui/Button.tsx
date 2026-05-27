import Link from "next/link";
import { type ComponentProps, type ReactNode } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost";

const base =
  "inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-semibold tracking-tight transition-all duration-200 disabled:opacity-60 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary:
    "relative overflow-hidden border border-emerald-400/30 bg-gradient-to-b from-emerald-400 to-emerald-600 text-slate-950 shadow-[0_1px_0_0_rgba(255,255,255,0.25)_inset,0_8px_24px_-8px_rgba(0,230,118,0.55)] hover:from-emerald-300 hover:to-emerald-500 hover:shadow-[0_1px_0_0_rgba(255,255,255,0.3)_inset,0_12px_32px_-10px_rgba(0,230,118,0.65)] focus:outline-none focus:ring-2 focus:ring-emerald-400/50 focus:ring-offset-2 focus:ring-offset-background active:scale-[0.98]",
  secondary:
    "border border-white/10 bg-white/[0.04] text-slate-100 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)] backdrop-blur-md hover:border-emerald-500/35 hover:bg-white/[0.08] hover:text-white focus:outline-none focus:ring-2 focus:ring-white/15 focus:ring-offset-2 focus:ring-offset-background",
  ghost: "text-slate-300 hover:bg-white/[0.06] hover:text-white",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return <button {...props} className={cx(base, variants[variant], className)} />;
}

export function ButtonLink({
  variant = "primary",
  className,
  children,
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant; children: ReactNode }) {
  return (
    <Link {...props} className={cx(base, variants[variant], className)}>
      {children}
    </Link>
  );
}
