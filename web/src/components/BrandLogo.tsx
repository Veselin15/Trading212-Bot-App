import Link from "next/link";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

type BrandVariant = "header" | "footer" | "auth";

const headerAuthClass: Record<
  "header" | "auth",
  { wrap: string; mark: string; wordmark: string }
> = {
  header: {
    wrap: "flex flex-row items-center gap-2.5",
    mark: "h-8 w-8 shrink-0",
    wordmark: "text-[17px] tracking-tight sm:text-lg",
  },
  auth: {
    wrap: "flex flex-col items-center gap-3",
    mark: "h-12 w-12 shrink-0",
    wordmark: "text-xl tracking-tight sm:text-2xl",
  },
};

function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cx("inline-flex items-baseline select-none leading-none", className)}>
      <span className="font-semibold tracking-tight text-white">Swift</span>
      <span className="bg-gradient-to-r from-emerald-300 via-emerald-400 to-teal-300 bg-clip-text font-semibold tracking-tight text-transparent">
        Trade
      </span>
    </span>
  );
}

export function BrandLogo({
  variant = "header",
  href = "/",
  className,
}: {
  variant?: BrandVariant;
  href?: string;
  className?: string;
}) {
  if (variant === "footer") {
    return (
      <Link
        href={href}
        className={cx(
          "group inline-flex max-w-[min(100%,240px)] transition-opacity hover:opacity-95",
          className,
        )}
      >
        <img
          src="/logo_text.png"
          alt="SwiftTrade"
          width={240}
          height={96}
          className="h-auto w-full max-h-[5.5rem] object-contain object-left opacity-95"
          decoding="async"
        />
      </Link>
    );
  }

  const v = headerAuthClass[variant];

  return (
    <Link
      href={href}
      className={cx("group inline-flex transition-opacity hover:opacity-95", v.wrap, className)}
      aria-label="SwiftTrade"
    >
      <img
        src="/logo.png"
        alt=""
        width={variant === "auth" ? 48 : 32}
        height={variant === "auth" ? 48 : 32}
        className={v.mark}
        decoding="async"
        fetchPriority={variant === "header" ? "high" : "auto"}
      />
      <Wordmark className={v.wordmark} />
    </Link>
  );
}
