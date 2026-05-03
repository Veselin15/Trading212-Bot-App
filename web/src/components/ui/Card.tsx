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
          "border-white/10 bg-white/5 backdrop-blur supports-[backdrop-filter]:bg-white/5",
        variant === "solid" && "border-white/10 bg-[#0A0A0A]",
        variant === "accent" && "border-emerald-500/35 bg-emerald-500/10",
        className,
      )}
    />
  );
}

