import { type ReactNode } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function SectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cx(
        "section-eyebrow mb-3",
        className,
      )}
    >
      <span className="h-px w-6 bg-gradient-to-r from-emerald-500/80 to-transparent" aria-hidden />
      {children}
    </p>
  );
}
