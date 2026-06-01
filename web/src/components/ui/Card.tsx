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
          "border-white/[0.08] bg-white/[0.04] backdrop-blur supports-[backdrop-filter]:bg-white/[0.04]",
        variant === "solid" && "border-white/[0.07] bg-[#07070b]",
        variant === "accent" &&
          "border-emerald-500/30 bg-emerald-500/[0.08] shadow-[0_0_40px_-16px_rgba(0,230,118,0.2)]",
        className,
      )}
    />
  );
}
