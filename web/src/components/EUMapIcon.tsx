import * as React from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function EUMapIcon({
  className,
  title = "European Union",
  variant = "solid",
}: {
  className?: string;
  title?: string;
  variant?: "solid" | "outline";
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      role="img"
      aria-label={title}
      className={cx("h-4 w-4", className)}
    >
      {/* Stylized Europe silhouette (iconic cue, not a political map). */}
      <path
        d="M14.95 3.25c-1.14.03-1.93.61-2.5 1.24-.52.57-.96 1.32-1.7 1.75-.62.36-1.43.41-2.07.72-.7.33-1.17.98-1.44 1.63-.26.64-.4 1.24-.92 1.73-.52.49-1.27.7-1.63 1.33-.42.74-.02 1.66.56 2.23.56.56 1.35.9 1.86 1.52.55.67.66 1.56 1.17 2.25.6.82 1.68 1.28 2.69 1.19.88-.08 1.64-.55 2.45-.92.86-.39 1.86-.57 2.59-1.22.65-.58.94-1.45 1.55-2.06.66-.66 1.66-.93 2.4-1.51.84-.65 1.35-1.7 1.17-2.74-.17-.98-.87-1.71-1.29-2.56-.4-.81-.58-1.76-1.2-2.45-.66-.74-1.75-1.16-2.69-1.13z"
        fill={variant === "outline" ? "none" : "currentColor"}
        stroke="currentColor"
        strokeWidth={variant === "outline" ? 1.25 : 0.8}
        opacity={variant === "outline" ? 0.9 : 0.92}
      />
    </svg>
  );
}

