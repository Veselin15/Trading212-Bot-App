import { type ComponentProps } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Label({ className, ...props }: ComponentProps<"label">) {
  return (
    <label
      {...props}
      className={cx("text-sm font-medium text-slate-200", className)}
    />
  );
}

