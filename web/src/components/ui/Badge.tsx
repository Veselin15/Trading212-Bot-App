import { type ComponentProps } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Badge({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      {...props}
      className={cx(
        "inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300 backdrop-blur",
        className,
      )}
    />
  );
}

