import Link from "next/link";
import { type ComponentProps, type ReactNode } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "primary",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={cx(
        "inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors disabled:opacity-60",
        variant === "primary" &&
          "bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/25 hover:bg-[#00E676] focus:outline-none focus:ring-2 focus:ring-emerald-400/55",
        variant === "secondary" &&
          "border border-white/10 bg-white/5 text-slate-50 backdrop-blur hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/10",
        variant === "ghost" && "text-slate-300 hover:bg-white/5",
        className,
      )}
    />
  );
}

export function ButtonLink({
  variant = "primary",
  className,
  children,
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant; children: ReactNode }) {
  return (
    <Link
      {...props}
      className={cx(
        "inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors",
        variant === "primary" &&
          "bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/25 hover:bg-[#00E676] focus:outline-none focus:ring-2 focus:ring-emerald-400/55",
        variant === "secondary" &&
          "border border-white/10 bg-white/5 text-slate-50 backdrop-blur hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/10",
        variant === "ghost" && "text-slate-300 hover:bg-white/5",
        className,
      )}
    >
      {children}
    </Link>
  );
}

