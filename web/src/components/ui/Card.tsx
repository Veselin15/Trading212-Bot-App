import { type ComponentProps } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type CardVariant = "glass" | "solid" | "accent";

export function Card({
  variant = "glass",
  className,
  ...props
}: ComponentProps<"div"> & { variant?: CardVariant }) {
  return (
    <div
      {...props}
      className={cx(
        "rounded-3xl border shadow-sm",
        variant === "glass" &&
          "border-slate-800/70 bg-white/5 backdrop-blur supports-[backdrop-filter]:bg-white/5",
        variant === "solid" && "border-slate-800/70 bg-slate-950/50",
        variant === "accent" && "border-sky-500/35 bg-sky-500/10",
        className,
      )}
    />
  );
}

