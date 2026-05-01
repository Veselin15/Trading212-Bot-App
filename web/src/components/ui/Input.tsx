import { type ComponentProps } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      {...props}
      className={cx(
        "flex h-11 w-full rounded-xl border border-slate-800/80 bg-white/5 px-4 text-sm text-slate-50 placeholder:text-slate-500 shadow-sm outline-none backdrop-blur",
        "focus:ring-2 focus:ring-sky-400/30 focus:border-sky-500/40",
        "disabled:opacity-60",
        className,
      )}
    />
  );
}

