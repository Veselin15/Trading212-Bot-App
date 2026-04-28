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
          "bg-zinc-950 text-white shadow-sm shadow-black/10 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200",
        variant === "secondary" &&
          "border border-black/10 bg-white/70 text-zinc-950 backdrop-blur hover:bg-white dark:border-white/10 dark:bg-black/30 dark:text-zinc-50 dark:hover:bg-black/50",
        variant === "ghost" && "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900",
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
          "bg-zinc-950 text-white shadow-sm shadow-black/10 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-200",
        variant === "secondary" &&
          "border border-black/10 bg-white/70 text-zinc-950 backdrop-blur hover:bg-white dark:border-white/10 dark:bg-black/30 dark:text-zinc-50 dark:hover:bg-black/50",
        variant === "ghost" && "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900",
        className,
      )}
    >
      {children}
    </Link>
  );
}

