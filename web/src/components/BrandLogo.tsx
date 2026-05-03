import Link from "next/link";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type BrandVariant = "header" | "footer" | "auth";

const variantClass: Record<BrandVariant, { wrap: string; mark: string; text: string }> = {
  header: {
    wrap: "flex flex-row items-center gap-2.5",
    mark: "h-8 w-8 shrink-0",
    text: "h-[22px] w-auto max-h-[22px] max-w-[min(48vw,220px)] object-contain object-left sm:max-w-[240px]",
  },
  footer: {
    wrap: "flex flex-row items-center gap-2",
    mark: "h-7 w-7 shrink-0 opacity-95",
    text: "h-[18px] w-auto max-h-[18px] max-w-[200px] object-contain object-left opacity-90",
  },
  auth: {
    wrap: "flex flex-col items-center gap-3",
    mark: "h-12 w-12 shrink-0",
    text: "h-7 w-auto max-h-7 max-w-[min(85vw,280px)] object-contain",
  },
};

export function BrandLogo({
  variant = "header",
  href = "/",
  className,
}: {
  variant?: BrandVariant;
  href?: string;
  className?: string;
}) {
  const v = variantClass[variant];

  return (
    <Link
      href={href}
      className={cx("group inline-flex transition-opacity hover:opacity-95", v.wrap, className)}
    >
      <img src="/logo.png" alt="" width={variant === "auth" ? 48 : variant === "footer" ? 28 : 32} height={variant === "auth" ? 48 : variant === "footer" ? 28 : 32} className={v.mark} decoding="async" fetchPriority={variant === "header" ? "high" : "auto"} />
      <img
        src="/logo_text.png"
        alt="SwiftTrade"
        className={v.text}
        decoding="async"
      />
    </Link>
  );
}
