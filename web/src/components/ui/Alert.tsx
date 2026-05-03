import { type ComponentProps } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type AlertVariant = "info" | "warning";

export function Alert({
  variant = "info",
  className,
  ...props
}: ComponentProps<"div"> & { variant?: AlertVariant }) {
  return (
    <div
      {...props}
      role="alert"
      className={cx(
        "rounded-2xl border px-4 py-3 text-sm",
        variant === "info" && "border-emerald-500/25 bg-emerald-500/10 text-emerald-100",
        variant === "warning" && "border-amber-500/25 bg-amber-500/10 text-amber-100",
        className,
      )}
    />
  );
}

