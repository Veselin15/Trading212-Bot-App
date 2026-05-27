export function PageBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-20 overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.45]"
        style={{
          background:
            "radial-gradient(ellipse 90% 55% at 50% -15%, rgba(0,230,118,0.14), transparent 58%), radial-gradient(ellipse 50% 40% at 0% 40%, rgba(16,185,129,0.06), transparent 55%), radial-gradient(ellipse 45% 35% at 100% 25%, rgba(52,211,153,0.05), transparent 50%)",
        }}
      />
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage: "radial-gradient(ellipse 85% 70% at 50% 0%, black 20%, transparent 72%)",
          WebkitMaskImage: "radial-gradient(ellipse 85% 70% at 50% 0%, black 20%, transparent 72%)",
        }}
      />
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}
